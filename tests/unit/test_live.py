from core.cost_engine import CostEngine
from core.order_manager import OrderManager
from live.live_engine import LiveEngine
from live.live_trader import LiveTradingEngine
from live.multi_strategy_runner import run_strategies
from live.order_manager import TradingOrderManager
from live.paper_trader import PaperTrader, PaperTradingEngine
from live.risk_manager import TradingRiskManager
from live.session_manager import SessionManager
from strategies.builtin.ma_crossover import MACrossoverStrategy


class DummyClient:
    def place_order(self, payload):
        return payload

    def cancel_order(self, payload):
        return payload


def test_paper_trader_and_live_engine(sample_frame, tmp_path):
    paper = PaperTrader(cash=1000)
    paper.execute("BTCIRT", "buy", 1, 100)
    assert paper.positions["BTCIRT"] == 1

    engine = LiveEngine(OrderManager(DummyClient()), confirm_required=False, stop_file=tmp_path / "stop")
    response = engine.on_bar(MACrossoverStrategy(), "BTCIRT", sample_frame, 30, confirm=True)
    assert response is None or response["symbol"] == "BTCIRT"


def test_multi_strategy_runner(sample_frame):
    results = run_strategies([MACrossoverStrategy()], "BTCIRT", sample_frame)
    assert "MACrossoverStrategy" in results


def test_session_manager_round_trip(tmp_path):
    manager = SessionManager(tmp_path)
    record = manager.create("paper", "MACrossoverStrategy", "BTCIRT", 1000, {"simulated": True})
    fetched = manager.get(record.session_id)
    assert fetched.session_id == record.session_id
    assert manager.list(status="active")


def test_paper_and_live_engines_generate_reports(sample_frame, tmp_path):
    strategy = MACrossoverStrategy()
    paper = PaperTradingEngine(
        strategy=strategy,
        symbol="BTCIRT",
        capital=1000,
        cost_engine=CostEngine(0.0015, 5.0, 5.0, seed=42),
        risk_manager=TradingRiskManager(1000, 0.5, 0.02, 0.1),
        report_dir=tmp_path / "paper",
    )
    for ts, row in sample_frame.iloc[:5].iterrows():
        paper.on_tick(str(ts), float(row["close"]), float(row["volume"]))
    paper_report = paper.report("paper-session")
    assert paper_report.exists()

    live = LiveTradingEngine(
        strategy=MACrossoverStrategy(),
        symbol="BTCIRT",
        capital=1000,
        order_manager=TradingOrderManager(DummyClient()),
        risk_manager=TradingRiskManager(1000, 0.5, 0.02, 0.1),
        report_dir=tmp_path / "live",
    )
    for ts, row in sample_frame.iloc[:5].iterrows():
        live.on_tick(str(ts), float(row["close"]), float(row["volume"]))
    live_report = live.report("live-session")
    assert live_report.exists()
