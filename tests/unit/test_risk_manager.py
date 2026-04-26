import pandas as pd

from core.risk_manager import RiskManager


def test_position_size_and_var():
    manager = RiskManager(risk_per_trade=0.01)
    assert manager.position_size(1000, 100) > 0
    returns = pd.Series([0.01, -0.02, 0.03])
    assert manager.historical_var(returns) >= 0


def test_max_drawdown():
    manager = RiskManager()
    curve = pd.Series([100, 120, 90, 130])
    assert manager.max_drawdown(curve) > 0
