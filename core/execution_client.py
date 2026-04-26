"""Execution client protocol shared by live and paper trading engines."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ExecutionClient(Protocol):
    """Minimal execution interface for order-based trading engines."""

    def place_order(self, payload: dict[str, Any]) -> Any:
        ...

    def cancel_order(self, payload: dict[str, Any]) -> Any:
        ...

    def get_orderbook(self, symbol: str) -> Any:
        ...
