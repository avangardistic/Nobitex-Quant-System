"""Abstract strategy contract.

Limitations:
- Strategies are expected to be pure and deterministic relative to provided inputs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from strategies.base.context import StrategyContext
from strategies.base.signal import Signal


class BaseStrategy(ABC):
    """Base interface for all strategies."""

    name = "BaseStrategy"

    def reset(self) -> None:
        """Reset any internal state before a new validation or backtest run."""

    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> dict[str, pd.Series]:
        """Return indicator series aligned to the input data."""

    @abstractmethod
    def generate_signal(self, context: StrategyContext) -> Signal | None:
        """Generate a signal using only the provided history and current bar."""
