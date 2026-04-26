"""Order lifecycle helpers for paper and live trading sessions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.execution_client import ExecutionClient


@dataclass
class ManagedOrder:
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float | None
    order_type: str
    status: str = "open"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    response: dict[str, Any] | None = None


class TradingOrderManager:
    """Persist lightweight order state around an execution client."""

    def __init__(self, client: ExecutionClient) -> None:
        self.client = client
        self.orders: dict[str, ManagedOrder] = {}
        self.audit_log: list[dict[str, Any]] = []

    def place(self, symbol: str, side: str, quantity: float, price: float | None = None, order_type: str = "market") -> ManagedOrder:
        payload = {"symbol": symbol, "side": side, "quantity": quantity, "type": order_type}
        if price is not None:
            payload["price"] = price
        response = self.client.place_order(payload)
        order_id = str(response.get("id") or response.get("order_id") or uuid.uuid4().hex[:12]) if isinstance(response, dict) else uuid.uuid4().hex[:12]
        order = ManagedOrder(order_id=order_id, symbol=symbol, side=side, quantity=quantity, price=price, order_type=order_type, response=response if isinstance(response, dict) else {"raw": response})
        self.orders[order_id] = order
        self.audit_log.append({"action": "place", "payload": payload, "response": order.response})
        return order

    def cancel(self, order_id: str) -> dict[str, Any]:
        response = self.client.cancel_order({"order_id": order_id, "status": "canceled"})
        if order_id in self.orders:
            self.orders[order_id].status = "canceled"
        self.audit_log.append({"action": "cancel", "order_id": order_id, "response": response})
        return response if isinstance(response, dict) else {"raw": response}

    def open_orders(self) -> list[ManagedOrder]:
        return [order for order in self.orders.values() if order.status == "open"]
