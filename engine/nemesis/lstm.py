import torch
import torch.nn as nn
from typing import Optional, Tuple
from .encoder import INPUT_SIZE


class NemesisLSTM(nn.Module):
    """
    The core of Nemesis AI.

    Reads the sequence of (board, move, aggression, quality) vectors
    representing the player's move history and outputs three predictions:

        move_pred    — where the player is likely to move next (from, to)
        style_pred   — how aggressive the player is (0=passive, 1=aggressive)
        quality_pred — how well the player is playing (0=blunder, 1=excellent)

    All three outputs share the same LSTM hidden state, meaning the same
    learned understanding of the player drives every prediction.
    """

    def __init__(
        self,
        input_size:  int = INPUT_SIZE,  # 778
        hidden_size: int = 128,
        num_layers:  int = 2,
        dropout:     float = 0.2,
    ):
        super(NemesisLSTM, self).__init__()

        self.hidden_size = hidden_size
        self.num_layers  = num_layers

        self.lstm = nn.LSTM(
            input_size  = input_size,
            hidden_size = hidden_size,
            num_layers  = num_layers,
            batch_first = True,
            dropout     = dropout if num_layers > 1 else 0.0,
        )

        # --- output heads ---
        # predicts the player's next from_square and to_square, normalized to [0,1]
        self.move_head = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Linear(64, 2),
            nn.Sigmoid(),
        )

        # predicts overall aggression profile (0=passive, 1=aggressive)
        self.style_head = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

        # predicts move quality (0=blunder, 1=excellent)
        self.quality_head = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(
        self,
        x:      torch.Tensor,
        hidden: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor,
               Optional[Tuple[torch.Tensor, torch.Tensor]]]:

        lstm_out, hidden = self.lstm(x, hidden)

        # use only the last timestep — it summarizes the full sequence
        last = lstm_out[:, -1, :]                          # (batch, hidden_size)

        move_pred    = self.move_head(last)                # (batch, 2)
        style_pred   = self.style_head(last)               # (batch, 1)
        quality_pred = self.quality_head(last)             # (batch, 1)

        return move_pred, style_pred, quality_pred, hidden

    def init_hidden(self, batch_size: int = 1) -> tuple[torch.Tensor, torch.Tensor]:
        """Returns a zeroed hidden state for the start of a new game."""
        return (
            torch.zeros(self.num_layers, batch_size, self.hidden_size),
            torch.zeros(self.num_layers, batch_size, self.hidden_size),
        )