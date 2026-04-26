"""Context passed to strategies during execution.

Limitations:
- Exposes read-only snapshots and does not provide broker state mutation.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class StrategyContext:
    """Per-bar strategy execution context."""

    symbol: str
    data: pd.DataFrame
    history: pd.DataFrame
    current_index: int
