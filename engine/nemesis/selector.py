import chess
import random
import math
from typing import Optional


# how many top candidate moves to consider at each MMR level
CANDIDATE_POOL_MIN = 20   # at MMR floor  — picks from many moves (weak)
CANDIDATE_POOL_MAX = 5    # at MMR ceiling — picks from few moves (sharp)

# aggression threshold — above this Nemesis starts playing solid/trapping lines
RECKLESS_THRESHOLD = 0.70

# quality threshold — below this the player is missing tactics
WEAK_THRESHOLD = 0.40

# how heavily the predicted player square influences Nemesis's choice
PREDICTION_WEIGHT = 0.35


def _mmr_factor(mmr: float) -> float:
    """Normalizes MMR to [0.0, 1.0] between floor and ceiling."""
    return max(0.0, min(1.0, (mmr - 1000) / 500))


def _candidate_pool_size(mmr: float) -> int:
    """
    At low MMR Nemesis considers many moves (more random).
    At high MMR it narrows to the strongest candidates (more precise).
    """
    factor = _mmr_factor(mmr)
    size = CANDIDATE_POOL_MIN - factor * (CANDIDATE_POOL_MIN - CANDIDATE_POOL_MAX)
    return max(CANDIDATE_POOL_MAX, round(size))


def _score_move(
    board:          chess.Board,
    move:           chess.Move,
    player_read:    dict,
    evaluator,
) -> float:
    """
    Scores a candidate move for Nemesis from multiple angles.
    Higher score = more desirable for Nemesis to play.

    Components:
        1. base evaluation  — how good is this move objectively
        2. style counter    — does it counter the player's profile
        3. prediction trap  — does it punish where the player is likely to go next
        4. mmr noise        — random noise that shrinks as MMR rises (weak AI feels weak)
    """
    mmr      = player_read["mmr"]
    factor   = _mmr_factor(mmr)
    score    = 0.0

    # --- 1. base evaluation ---
    base = evaluator.evaluate(board)
    board.push(move)
    after = evaluator.evaluate(board)
    board.pop()

    # Nemesis plays black — lower centipawn score is better for black
    eval_delta = base - after
    base_weight = 0.5 + 0.5 * factor   # 0.5 at floor, 1.0 at ceiling
    score += eval_delta * base_weight * 0.01

    # --- 2. style counter ---
    aggression   = player_read["aggression"]
    quality      = player_read["quality"]
    mom_agg      = player_read["momentum_agg"]
    mom_qual     = player_read["momentum_qual"]

    # against a reckless aggressor — prefer solid, trapping moves
    if aggression > RECKLESS_THRESHOLD and quality < WEAK_THRESHOLD:
        # reward moves that keep the position closed and safe
        board.push(move)
        if not board.is_check():
            # closing the center against a reckless attacker is good
            piece = board.piece_at(move.to_square)
            if piece and piece.piece_type == chess.PAWN:
                score += 0.3 * factor

        # reward moves that set up discovered attacks or forks
        if board.is_attacked_by(chess.BLACK, move.to_square):
            score += 0.2 * factor
        board.pop()

    # against a passive player — press with piece activity
    elif aggression < 0.35:
        board.push(move)
        # reward moves that increase black's piece mobility
        black_mobility = len(list(board.legal_moves))
        score += (black_mobility / 30.0) * 0.2 * factor
        board.pop()

    # if player is currently on a confident momentum streak — disrupt it
    if mom_agg > 0.65 and mom_qual > 0.60:
        # reward moves that introduce complications
        if board.is_capture(move):
            score += 0.25 * factor

    # --- 3. prediction trap ---
    # if Nemesis predicts where the player is going next,
    # reward moves that contest or control that square
    predicted_to = player_read.get("predicted_to")
    if predicted_to is not None:
        board.push(move)
        # does this move attack the square the player is predicted to go to?
        if board.is_attacked_by(chess.BLACK, predicted_to):
            score += PREDICTION_WEIGHT * factor
        board.pop()

    # --- 4. mmr noise ---
    # at low MMR Nemesis makes noisier choices — it feels genuinely weak
    noise_scale = 1.0 - factor   # 1.0 at floor, 0.0 at ceiling
    score += random.gauss(0, noise_scale * 0.2)

    return score


def select_move(
    board:       chess.Board,
    player_read: dict,
    evaluator,
) -> Optional[chess.Move]:
    """
    Selects Nemesis's move given the current board and player profile.

    Process:
        1. generate all legal moves for black
        2. narrow to a candidate pool sized by MMR
        3. score each candidate against the player profile
        4. return the highest scoring move
    """
    legal = list(board.legal_moves)
    if not legal:
        return None

    # checkmate or stalemate already — nothing to select
    if board.is_game_over():
        return None

    mmr        = player_read["mmr"]
    pool_size  = _candidate_pool_size(mmr)

    # pre-filter: get a rough ordering by base evaluation
    # so the candidate pool isn't purely random at any MMR
    def quick_eval(move):
        board.push(move)
        val = evaluator.evaluate(board)
        board.pop()
        return val

    # sort ascending — black wants lower centipawn scores
    sorted_moves = sorted(legal, key=quick_eval)

    # take the top pool_size moves as candidates
    # at low MMR this is a large pool (more randomness baked in via noise)
    # at high MMR this is a tight pool of strong moves
    candidates = sorted_moves[:pool_size]

    # score each candidate with the full profiling system
    scored = [
        (move, _score_move(board, move, player_read, evaluator))
        for move in candidates
    ]

    # pick the highest scoring move
    best_move = max(scored, key=lambda x: x[1])[0]
    return best_move