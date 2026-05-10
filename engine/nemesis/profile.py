import numpy as np
from collections import deque


# MMR boundaries — AI starts at floor and climbs toward ceiling
MMR_FLOOR   = 1000
MMR_CEILING = 1500

# how many moves before MMR reaches its ceiling
MMR_FULL_RAMP = 30

# momentum window size — how many recent moves define current state
MOMENTUM_WINDOW = 6

# forgetting factor — older moves decay by this per step (0.95 = 5% decay per move)
FORGET_FACTOR = 0.95


class PlayerProfile:
    """
    Maintains a live model of the human player built entirely
    from their own moves during the match.

    Tracks:
        - overall aggression and quality scores (exponential moving average)
        - short-term momentum (last N moves)
        - full weighted move history for LSTM training
        - current MMR estimate of the AI's strength
    """

    def __init__(self):
        # long-term style scores — start neutral
        self.aggression_score = 0.5
        self.quality_score    = 0.5

        # short-term momentum ring buffer
        self.momentum_window: deque[tuple[float, float]] = deque(maxlen=MOMENTUM_WINDOW)

        # full move history as encoded 778-float vectors
        self.move_history: list[np.ndarray] = []

        # current AI strength
        self.mmr = MMR_FLOOR

    # ------------------------------------------------------------------
    # recording a move
    # ------------------------------------------------------------------

    def record_move(self, full_vec: np.ndarray, aggression: float, quality: float):
        """
        Called once per player move.
        Updates history, momentum, long-term scores, and MMR.
        """
        self.move_history.append(full_vec)
        self.momentum_window.append((aggression, quality))
        self._update_long_term_scores()
        self._update_mmr()

    # ------------------------------------------------------------------
    # long-term scores
    # ------------------------------------------------------------------

    def _update_long_term_scores(self):
        """
        Exponential moving average — recent moves carry more weight
        but the entire history still influences the score.
        """
        mom_aggression, mom_quality = self.get_momentum()
        self.aggression_score = self.aggression_score * 0.7 + mom_aggression * 0.3
        self.quality_score    = self.quality_score    * 0.7 + mom_quality    * 0.3

    # ------------------------------------------------------------------
    # momentum
    # ------------------------------------------------------------------

    def get_momentum(self) -> tuple[float, float]:
        """
        Returns the average aggression and quality over the last N moves.
        Reflects the player's current mental state rather than overall style.
        """
        if not self.momentum_window:
            return 0.5, 0.5
        avg_aggression = sum(a for a, _ in self.momentum_window) / len(self.momentum_window)
        avg_quality    = sum(q for _, q in self.momentum_window) / len(self.momentum_window)
        return avg_aggression, avg_quality

    # ------------------------------------------------------------------
    # forgetting curve
    # ------------------------------------------------------------------

    def get_weighted_history(self) -> list[tuple[np.ndarray, float]]:
        """
        Returns move history with exponential decay weights.
        The most recent move always has weight 1.0.
        Older moves fade so style shifts mid-game are picked up.

        Example with FORGET_FACTOR=0.95 and 5 moves:
            move 0 → weight 0.81
            move 1 → weight 0.86
            move 2 → weight 0.90
            move 3 → weight 0.95
            move 4 → weight 1.00  (most recent)
        """
        n = len(self.move_history)
        return [
            (vec, FORGET_FACTOR ** (n - 1 - i))
            for i, vec in enumerate(self.move_history)
        ]

    # ------------------------------------------------------------------
    # MMR
    # ------------------------------------------------------------------

    def _update_mmr(self):
        """
        MMR climbs as:
            - more data is collected (data_factor)
            - player quality is higher (quality_factor)

        A stronger player makes Nemesis climb faster —
        they give it better signal to learn from.
        """
        data_factor    = min(len(self.move_history) / MMR_FULL_RAMP, 1.0)
        quality_factor = self.quality_score
        self.mmr       = MMR_FLOOR + (MMR_CEILING - MMR_FLOOR) * data_factor * quality_factor

    # ------------------------------------------------------------------
    # summary
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        """Returns a snapshot of the profile for logging and debugging."""
        mom_agg, mom_qual = self.get_momentum()
        return {
            "mmr":               round(self.mmr),
            "aggression":        round(self.aggression_score, 3),
            "quality":           round(self.quality_score, 3),
            "momentum_agg":      round(mom_agg, 3),
            "momentum_qual":     round(mom_qual, 3),
            "moves_recorded":    len(self.move_history),
        }