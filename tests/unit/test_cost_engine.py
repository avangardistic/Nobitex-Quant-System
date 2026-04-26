from core.cost_engine import CostEngine


def test_cost_engine_apply_and_hash():
    engine = CostEngine(commission_rate=0.001, spread_bps=5, slippage_bps=5, seed=42)
    fill = engine.apply(100, 2, "buy", avg_volume=1000, volatility=0.01)
    assert fill.effective_price > 100
    assert fill.commission > 0
    assert len(engine.reproducibility_hash([{"a": 1}])) == 64
