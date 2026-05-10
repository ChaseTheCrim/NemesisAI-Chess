import chess
import chess.engine
import os
import sys
from typing import Optional


# centipawn delta considered a strong move — used for quality normalization
QUALITY_SCALE = 200.0

# evaluation time limit per position in seconds — kept tiny to stay invisible
EVAL_TIME_LIMIT = 0.05


def _find_engine_binary() - Optional[str]
    
    Locates the evaluation backend binary.
    Searches in order
        1. same directory as this file
        2. engine directory relative to project root
        3. system PATH
    
    candidates = [
        os.path.join(os.path.dirname(__file__), bin, evaluator.exe),
        os.path.join(os.path.dirname(__file__), bin, evaluator),
        os.path.join(os.path.dirname(__file__), .., bin, evaluator.exe),
        os.path.join(os.path.dirname(__file__), .., bin, evaluator),
    ]

    for path in candidates
        if os.path.isfile(path)
            return os.path.abspath(path)

    # fall back to PATH
    import shutil
    system = shutil.which(evaluator) or shutil.which(stockfish)
    if system
        return system

    return None


class Evaluator
    
    Silent move quality backend.

    Runs entirely in the background — it never selects moves,
    never influences the game directly, and is never exposed
    to the frontend. Its only job is to score the quality
    of the player's moves so the LSTM has a meaningful
    training signal.
    

    def __init__(self)
        self._engine = None
        self._available = False
        self._init_engine()

    def _init_engine(self)
        binary = _find_engine_binary()
        if not binary
            print([NEMESIS] Evaluator backend not found — quality scoring disabled.,
                  file=sys.stderr, flush=True)
            return

        try
            self._engine    = chess.engine.SimpleEngine.popen_uci(binary)
            self._available = True
        except Exception as e
            print(f[NEMESIS] Evaluator failed to start {e},
                  file=sys.stderr, flush=True)

    # ------------------------------------------------------------------
    # public interface
    # ------------------------------------------------------------------

    def evaluate(self, board chess.Board) - float
        
        Returns the centipawn score of the position from white's perspective.
        Returns 0.0 if the evaluator is unavailable.
        
        if not self._available or self._engine is None
            return 0.0

        try
            result = self._engine.analyse(
                board,
                chess.engine.Limit(time=EVAL_TIME_LIMIT),
            )
            score = result.get(score)
            if score is None
                return 0.0

            white_score = score.white()

            if white_score.is_mate()
                mate = white_score.mate()
                return 10000.0 if (mate is not None and mate  0) else -10000.0

            return float(white_score.score(mate_score=10000) or 0.0)

        except Exception
            return 0.0

    def score_move(self, board chess.Board, move chess.Move) - float
        
        Scores a single move as a quality value in [0.0, 1.0].

            0.0 — serious blunder
            0.5 — neutral  average
            1.0 — excellent move

        Quality is the centipawn improvement the move makes
        for the player who made it, normalized to [0, 1].
        
        if not self._available
            return 0.5  # neutral fallback — don't penalize without data

        score_before = self.evaluate(board)

        board.push(move)
        score_after = self.evaluate(board)
        board.pop()

        # delta from the moving player's perspective
        delta = score_after - score_before
        if board.turn == chess.BLACK
            delta = -delta  # flip — black wants lower centipawn scores

        # normalize +QUALITY_SCALE cp or better → 1.0, -QUALITY_SCALE or worse → 0.0
        quality = (delta + QUALITY_SCALE)  (2.0  QUALITY_SCALE)
        return float(max(0.0, min(1.0, quality)))

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def close(self)
        Cleanly shuts down the backend. Call on game exit.
        if self._engine
            try
                self._engine.quit()
            except Exception
                pass
            self._engine    = None
            self._available = False

    def is_available(self) - bool
        return self._available

    def __del__(self)
        self.close()