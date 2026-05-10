"""
Classical heuristic position evaluator for Nemesis AI.

Based on standard chess principles documented in chess theory since the 1970s:
    - Material count (relative piece values)
    - Piece-square tables (positional value of each piece on each square)
    - Mobility (legal move count)
    - King safety bonuses
    - Pawn structure penalties

Returns centipawn-like scores from white's perspective. Used as the
quality signal for Nemesis's online learning — it tells the LSTM
how good or bad the player's moves are without ever picking moves itself.
"""

import chess


# ----------------------------------------------------------------------
# material values
# ----------------------------------------------------------------------
PIECE_VALUES = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   0,
}


# ----------------------------------------------------------------------
# piece-square tables — bonuses/penalties for each piece on each square
# from white's perspective. Read top-to-bottom, rank 8 first, rank 1 last.
# ----------------------------------------------------------------------

PAWN_PST = [
     0,   0,   0,   0,   0,   0,   0,   0,
    50,  50,  50,  50,  50,  50,  50,  50,
    10,  10,  20,  30,  30,  20,  10,  10,
     5,   5,  10,  25,  25,  10,   5,   5,
     0,   0,   0,  20,  20,   0,   0,   0,
     5,  -5, -10,   0,   0, -10,  -5,   5,
     5,  10,  10, -20, -20,  10,  10,   5,
     0,   0,   0,   0,   0,   0,   0,   0,
]

KNIGHT_PST = [
   -50, -40, -30, -30, -30, -30, -40, -50,
   -40, -20,   0,   0,   0,   0, -20, -40,
   -30,   0,  10,  15,  15,  10,   0, -30,
   -30,   5,  15,  20,  20,  15,   5, -30,
   -30,   0,  15,  20,  20,  15,   0, -30,
   -30,   5,  10,  15,  15,  10,   5, -30,
   -40, -20,   0,   5,   5,   0, -20, -40,
   -50, -40, -30, -30, -30, -30, -40, -50,
]

BISHOP_PST = [
   -20, -10, -10, -10, -10, -10, -10, -20,
   -10,   0,   0,   0,   0,   0,   0, -10,
   -10,   0,   5,  10,  10,   5,   0, -10,
   -10,   5,   5,  10,  10,   5,   5, -10,
   -10,   0,  10,  10,  10,  10,   0, -10,
   -10,  10,  10,  10,  10,  10,  10, -10,
   -10,   5,   0,   0,   0,   0,   5, -10,
   -20, -10, -10, -10, -10, -10, -10, -20,
]

ROOK_PST = [
     0,   0,   0,   0,   0,   0,   0,   0,
     5,  10,  10,  10,  10,  10,  10,   5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
     0,   0,   0,   5,   5,   0,   0,   0,
]

QUEEN_PST = [
   -20, -10, -10,  -5,  -5, -10, -10, -20,
   -10,   0,   0,   0,   0,   0,   0, -10,
   -10,   0,   5,   5,   5,   5,   0, -10,
    -5,   0,   5,   5,   5,   5,   0,  -5,
     0,   0,   5,   5,   5,   5,   0,  -5,
   -10,   5,   5,   5,   5,   5,   0, -10,
   -10,   0,   5,   0,   0,   0,   0, -10,
   -20, -10, -10,  -5,  -5, -10, -10, -20,
]

# king prefers safety in the corner during opening/middlegame
KING_PST_MIDGAME = [
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -20, -30, -30, -40, -40, -30, -30, -20,
   -10, -20, -20, -20, -20, -20, -20, -10,
    20,  20,   0,   0,   0,   0,  20,  20,
    20,  30,  10,   0,   0,  10,  30,  20,
]

# in the endgame king becomes active and prefers center
KING_PST_ENDGAME = [
   -50, -40, -30, -20, -20, -30, -40, -50,
   -30, -20, -10,   0,   0, -10, -20, -30,
   -30, -10,  20,  30,  30,  20, -10, -30,
   -30, -10,  30,  40,  40,  30, -10, -30,
   -30, -10,  30,  40,  40,  30, -10, -30,
   -30, -10,  20,  30,  30,  20, -10, -30,
   -30, -30,   0,   0,   0,   0, -30, -30,
   -50, -30, -30, -30, -30, -30, -30, -50,
]

PST = {
    chess.PAWN:   PAWN_PST,
    chess.KNIGHT: KNIGHT_PST,
    chess.BISHOP: BISHOP_PST,
    chess.ROOK:   ROOK_PST,
    chess.QUEEN:  QUEEN_PST,
}


# ----------------------------------------------------------------------
# evaluator
# ----------------------------------------------------------------------

# centipawn delta considered a strong move — used for quality normalization
QUALITY_SCALE = 200.0

# total non-pawn material below this threshold = endgame
ENDGAME_MATERIAL_THRESHOLD = 1500


class Evaluator:
    """
    Heuristic position evaluator built entirely from classical chess principles.
    Returns centipawn-style scores from white's perspective.
    """

    def __init__(self):
        self._available = True   # always available — pure Python, no binary

    # ------------------------------------------------------------------
    # public interface — matches the original Evaluator API
    # ------------------------------------------------------------------

    def evaluate(self, board: chess.Board) -> float:
        if board.is_checkmate():
            return -10000.0 if board.turn == chess.WHITE else 10000.0
        if board.is_stalemate() or board.is_insufficient_material():
            return 0.0

        is_endgame = self._is_endgame(board)

        score  = self._material_score(board)
        score += self._positional_score(board, is_endgame)
        score += self._mobility_score(board)
        score += self._pawn_structure_score(board)
        score += self._threat_score(board)

        return float(score)

    def score_move(self, board: chess.Board, move: chess.Move) -> float:
        score_before = self.evaluate(board)

        board.push(move)
        score_after = self.evaluate(board)
        board.pop()

        delta = score_after - score_before
        if board.turn == chess.BLACK:
            delta = -delta

        quality = (delta + QUALITY_SCALE) / (2.0 * QUALITY_SCALE)
        return float(max(0.0, min(1.0, quality)))

    def is_available(self) -> bool:
        return True

    def close(self):
        pass

    # ------------------------------------------------------------------
    # internal scoring components
    # ------------------------------------------------------------------

    def _is_endgame(self, board: chess.Board) -> bool:
        non_pawn_material = 0
        for piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
            non_pawn_material += len(board.pieces(piece_type, chess.WHITE)) * PIECE_VALUES[piece_type]
            non_pawn_material += len(board.pieces(piece_type, chess.BLACK)) * PIECE_VALUES[piece_type]
        return non_pawn_material < ENDGAME_MATERIAL_THRESHOLD

    def _material_score(self, board: chess.Board) -> int:
        score = 0
        for piece_type, value in PIECE_VALUES.items():
            score += len(board.pieces(piece_type, chess.WHITE)) * value
            score -= len(board.pieces(piece_type, chess.BLACK)) * value
        return score

    def _positional_score(self, board: chess.Board, is_endgame: bool) -> int:
        score = 0
        for square, piece in board.piece_map().items():
            white_index = chess.square_mirror(square)
            black_index = square

            if piece.piece_type == chess.KING:
                table = KING_PST_ENDGAME if is_endgame else KING_PST_MIDGAME
            else:
                table = PST[piece.piece_type]

            if piece.color == chess.WHITE:
                score += table[white_index]
            else:
                score -= table[black_index]
        return score

    def _mobility_score(self, board: chess.Board) -> int:
        white_moves = self._count_legal_moves(board, chess.WHITE)
        black_moves = self._count_legal_moves(board, chess.BLACK)
        return white_moves - black_moves

    def _count_legal_moves(self, board: chess.Board, color: bool) -> int:
        if board.turn == color:
            return board.legal_moves.count()
        try:
            board.push(chess.Move.null())
            count = board.legal_moves.count()
            board.pop()
            return count
        except Exception:
            return 0

    def _pawn_structure_score(self, board: chess.Board) -> int:
        score = 0
        for color in (chess.WHITE, chess.BLACK):
            sign = 1 if color == chess.WHITE else -1
            pawns = board.pieces(chess.PAWN, color)

            pawn_files = [chess.square_file(sq) for sq in pawns]

            # doubled pawns
            for f in set(pawn_files):
                count = pawn_files.count(f)
                if count > 1:
                    score -= sign * 15 * (count - 1)

            # isolated pawns
            for sq in pawns:
                f = chess.square_file(sq)
                neighbors = {f - 1, f + 1}
                if not neighbors.intersection(pawn_files):
                    score -= sign * 20

        return score

    # ------------------------------------------------------------------
    # threat detection — the key to not blundering pieces
    # ------------------------------------------------------------------

    def _threat_score(self, board: chess.Board) -> int:
        """
        Detects hanging pieces — pieces that can be captured for
        net material loss. This is a simplified Static Exchange
        Evaluation (SEE) that catches simple one-move tactics
        invisible to a purely static position evaluator.

        For each piece on the board:
            - find the lowest-value enemy attacker on its square
            - if the attacker is worth less than the piece, AND
              the piece has no defender of equal or lower value,
              the piece is considered hanging
            - subtract the loss from the side that owns the piece
        """
        score = 0

        for square, piece in board.piece_map().items():
            # kings can't be captured, skip
            if piece.piece_type == chess.KING:
                continue

            piece_value = PIECE_VALUES[piece.piece_type]
            enemy_color = not piece.color

            attackers = board.attackers(enemy_color, square)
            if not attackers:
                continue

            # find the lowest-value attacker
            attacker_pieces = [board.piece_at(sq) for sq in attackers]
            min_attacker_value = min(
                PIECE_VALUES[p.piece_type] for p in attacker_pieces if p is not None
            )

            # if attacker is worth more than the target, no immediate threat
            if min_attacker_value >= piece_value:
                continue

            # check defenders
            defenders = board.attackers(piece.color, square)

            if not defenders:
                # completely hanging — full piece loss
                loss = piece_value
            else:
                # if any defender is worth less than the threatened piece,
                # the exchange is roughly safe
                defender_pieces = [board.piece_at(sq) for sq in defenders]
                min_defender_value = min(
                    PIECE_VALUES[p.piece_type] for p in defender_pieces if p is not None
                )
                if min_defender_value <= piece_value:
                    # the trade is acceptable, no significant loss
                    continue
                # only defended by higher-value pieces — net loss
                loss = piece_value - min_attacker_value

            # only the side to move can prevent the threat,
            # so the threat hits the OTHER side
            if piece.color == chess.WHITE:
                # white's piece is hanging, but white can move first
                if board.turn == chess.WHITE:
                    score -= loss * 0.3   # white can defend, partial threat
                else:
                    score -= loss         # black to move and capture
            else:
                if board.turn == chess.BLACK:
                    score += loss * 0.3
                else:
                    score += loss

        return int(score)