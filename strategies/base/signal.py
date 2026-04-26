"""Signal objects exchanged between strategies and execution engines.

Limitations:
- Supports one symbol and one target action per signal.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Signal:
    """Trading signal emitted by a strategy."""

    timestamp: object
    symbol: str
    action: str
    confidence: float = 1.0
    stop_loss: float | None = None
    take_profit: float | None = None
    metadata: dict | None = None
