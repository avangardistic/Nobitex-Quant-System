"""Order management for live and simulated trading.

Limitations:
- Supports market-style orders and simple cancellation only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.client import NobitexClient


@dataclass
class OrderRequest:
    symbol: str
    side: str
    quantity: float
    price: float | None = None
    order_type: str = "market"


class OrderManager:
    """Coordinate order placement and cancellation."""

    def __init__(self, client: NobitexClient) -> None:
        self.client = client

    def place(self, order: OrderRequest) -> Any:
        payload = {
            "symbol": order.symbol,
            "type": order.order_type,
            "side": order.side,
            "quantity": order.quantity,
        }
        if order.price is not None:
            payload["price"] = order.price
        return self.client.place_order(payload)

    def cancel(self, order_id: str) -> Any:
        return self.client.cancel_order({"order_id": order_id, "status": "canceled"})
