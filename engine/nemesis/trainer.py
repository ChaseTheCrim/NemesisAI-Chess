import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import chess

from .encoder   import encode_full
from .lstm      import NemesisLSTM
from .profile   import PlayerProfile
from .evaluator import Evaluator


# loss weights — move prediction matters most
WEIGHT_MOVE    = 0.6
WEIGHT_STYLE   = 0.2
WEIGHT_QUALITY = 0.2

# gradient clipping threshold
GRAD_CLIP = 1.0

# minimum moves before training begins — need a sequence to learn from
MIN_HISTORY = 2


class NemesisTrainer:
    """
    Orchestrates online learning for Nemesis AI.

    Called once per player move via on_player_move().
    After each call:
        - the player profile is updated
        - the LSTM backpropagates on the new move
        - the hidden state carries forward into the next move

    The LSTM never resets mid-game — its hidden state is the
    accumulated memory of everything the player has done.
    """

    def __init__(self):
        self.model     = NemesisLSTM()
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        self.profile   = PlayerProfile()
        self.evaluator = Evaluator()
        self.hidden    = None  # persists across moves

        self.loss_move_fn    = nn.MSELoss()
        self.loss_style_fn   = nn.MSELoss()
        self.loss_quality_fn = nn.MSELoss()

    # ------------------------------------------------------------------
    # aggression signal
    # ------------------------------------------------------------------

    def _compute_aggression(self, board: chess.Board, move: chess.Move) -> float:
        """
        Scores how aggressive a move is based on observable board events.
        Returns a value in [0.0, 1.0].
        """
        score = 0.0

        # captures — core of aggression
        if board.is_capture(move):
            score += 0.4
            # capturing into a defended square = risky / reckless
            if board.is_attacked_by(not board.turn, move.to_square):
                score += 0.15

        # giving check
        board.push(move)
        if board.is_check():
            score += 0.3
        board.pop()

        # pawn advances past the midpoint
        piece = board.piece_at(move.from_square)
        if piece and piece.piece_type == chess.PAWN:
            to_rank = chess.square_rank(move.to_square)
            if piece.color == chess.WHITE and to_rank >= 4:
                score += 0.15
            elif piece.color == chess.BLACK and to_rank <= 3:
                score += 0.15

        return min(score, 1.0)

    # ------------------------------------------------------------------
    # main entry point
    # ------------------------------------------------------------------

    def on_player_move(self, board: chess.Board, move: chess.Move):
        """
        Called immediately after the player makes a legal move.
        board must be the state BEFORE the move is pushed.

        Steps:
            1. compute aggression and quality signals
            2. encode the full input vector
            3. record in player profile
            4. train the LSTM if enough history exists
        """

        aggression = self._compute_aggression(board, move)
        quality    = self.evaluator.score_move(board, move)
        full_vec   = encode_full(board, move, aggression, quality)

        self.profile.record_move(full_vec, aggression, quality)

        if len(self.profile.move_history) < MIN_HISTORY:
            self._log()
            return

        self._train_step()
        self._log()

    # ------------------------------------------------------------------
    # training
    # ------------------------------------------------------------------

    def _train_step(self):
        weighted_history = self.profile.get_weighted_history()

        # inputs  = all moves except the last
        # target  = the last move (what we're learning to predict)
        inputs = np.array([vec for vec, _ in weighted_history[:-1]])
        target_vec = weighted_history[-1][0]

        # shape: (1, seq_len, 778)
        x = torch.FloatTensor(inputs).unsqueeze(0)

        # targets
        target_move = torch.FloatTensor(
            [[target_vec[774], target_vec[775]]]
        )                                                          # (1, 2)
        target_style   = torch.FloatTensor([[target_vec[776]]])   # (1, 1)
        target_quality = torch.FloatTensor([[target_vec[777]]])   # (1, 1)

        # detach hidden so gradients don't flow across move boundaries
        hidden = (
            (self.hidden[0].detach(), self.hidden[1].detach())
            if self.hidden else None
        )

        self.model.train()
        self.optimizer.zero_grad()

        move_pred, style_pred, quality_pred, self.hidden = self.model(x, hidden)

        loss_move    = self.loss_move_fn   (move_pred,    target_move)
        loss_style   = self.loss_style_fn  (style_pred,   target_style)
        loss_quality = self.loss_quality_fn(quality_pred, target_quality)

        total_loss = (
            WEIGHT_MOVE    * loss_move    +
            WEIGHT_STYLE   * loss_style   +
            WEIGHT_QUALITY * loss_quality
        )

        total_loss.backward()

        # clip gradients — prevents exploding updates on short sequences
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), GRAD_CLIP)

        self.optimizer.step()

    # ------------------------------------------------------------------
    # inference — what does Nemesis think the player will do next?
    # ------------------------------------------------------------------

    def predict_player(self, board: chess.Board) -> dict:
        """
        Returns Nemesis's current read on the player.
        Used by the selector to inform move choice.
        """
        if not self.profile.move_history:
            return {
                "predicted_from": None,
                "predicted_to":   None,
                "aggression":     0.5,
                "quality":        0.5,
                "momentum_agg":   0.5,
                "momentum_qual":  0.5,
                "mmr":            self.profile.mmr,
            }

        x = torch.FloatTensor(
            np.array([vec for vec, _ in self.profile.get_weighted_history()])
        ).unsqueeze(0)

        self.model.eval()
        with torch.no_grad():
            move_pred, style_pred, quality_pred, _ = self.model(x, None)

        predicted_from = round(float(move_pred[0][0]) * 63)
        predicted_to   = round(float(move_pred[0][1]) * 63)

        mom_agg, mom_qual = self.profile.get_momentum()

        return {
            "predicted_from": predicted_from,
            "predicted_to":   predicted_to,
            "aggression":     float(style_pred[0][0]),
            "quality":        float(quality_pred[0][0]),
            "momentum_agg":   mom_agg,
            "momentum_qual":  mom_qual,
            "mmr":            self.profile.mmr,
        }

    # ------------------------------------------------------------------
    # logging
    # ------------------------------------------------------------------

    def _log(self):
        s = self.profile.summary()
        print(
            f"[NEMESIS] MMR: {s['mmr']} | "
            f"Aggression: {s['aggression']} | "
            f"Quality: {s['quality']} | "
            f"Momentum: ({s['momentum_agg']}, {s['momentum_qual']}) | "
            f"Moves: {s['moves_recorded']}",
            flush=True,
        )

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def close(self):
        self.evaluator.close()