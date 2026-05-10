import chess
import numpy as np

# Maps each (piece_type, color) pair to a channel index in the 12-plane board matrix
PIECE_TO_CHANNEL = {
    (chess.PAWN,   chess.WHITE): 0,
    (chess.KNIGHT, chess.WHITE): 1,
    (chess.BISHOP, chess.WHITE): 2,
    (chess.ROOK,   chess.WHITE): 3,
    (chess.QUEEN,  chess.WHITE): 4,
    (chess.KING,   chess.WHITE): 5,
    (chess.PAWN,   chess.BLACK): 6,
    (chess.KNIGHT, chess.BLACK): 7,
    (chess.BISHOP, chess.BLACK): 8,
    (chess.ROOK,   chess.BLACK): 9,
    (chess.QUEEN,  chess.BLACK): 10,
    (chess.KING,   chess.BLACK): 11,
}


def encode_board(board: chess.Board) -> np.ndarray:
    """
    Encodes the board into a flat float32 vector of length 774.

    Structure:
        [0:768]   — 12 binary 8x8 planes, one per piece type per color
        [768:774] — 6 scalar context features
    """
    planes = np.zeros((12, 8, 8), dtype=np.float32)

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            channel = PIECE_TO_CHANNEL[(piece.piece_type, piece.color)]
            row = 7 - (square // 8)  # rank 1 → row 7, consistent with Qt board render
            col = square % 8
            planes[channel][row][col] = 1.0

    board_vec = planes.flatten()  # 768 floats

    extras = np.array([
        1.0 if board.turn == chess.WHITE else 0.0,
        1.0 if board.has_kingside_castling_rights(chess.WHITE)  else 0.0,
        1.0 if board.has_queenside_castling_rights(chess.WHITE) else 0.0,
        1.0 if board.has_kingside_castling_rights(chess.BLACK)  else 0.0,
        1.0 if board.has_queenside_castling_rights(chess.BLACK) else 0.0,
        float(board.ep_square) / 63.0 if board.ep_square else 0.0,
    ], dtype=np.float32)  # 6 floats

    return np.concatenate([board_vec, extras])  # 774 floats total


def encode_move(move: chess.Move) -> np.ndarray:
    """
    Encodes a move as a float32 vector of length 2.
    Both squares are normalized to [0, 1].
    """
    return np.array([
        move.from_square / 63.0,
        move.to_square   / 63.0,
    ], dtype=np.float32)


def encode_full(board: chess.Board, move: chess.Move,
                aggression: float, quality: float) -> np.ndarray:
    """
    Combines board encoding, move encoding, and the two context scalars
    into the full 778-float input vector fed to the LSTM each timestep.

    Structure:
        [0:774]   — encoded board state
        [774:776] — encoded move (from, to)
        [776]     — aggression score  (0=passive, 1=aggressive)
        [777]     — quality score     (0=blunder, 1=excellent)
    """
    return np.concatenate([
        encode_board(board),
        encode_move(move),
        np.array([aggression, quality], dtype=np.float32),
    ])  # 778 floats total


# input size constant used by the LSTM so it never needs to hardcode 778
INPUT_SIZE = 778