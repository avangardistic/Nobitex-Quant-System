from core.order_manager import OrderManager, OrderRequest


class DummyClient:
    def place_order(self, payload):
        return payload

    def cancel_order(self, payload):
        return payload


def test_place_and_cancel():
    manager = OrderManager(DummyClient())
    response = manager.place(OrderRequest(symbol="BTCIRT", side="buy", quantity=1, price=100))
    assert response["symbol"] == "BTCIRT"
    assert manager.cancel("1")["status"] == "canceled"
