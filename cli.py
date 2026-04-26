"""CLI entrypoint for the Nobitex quant system.

Limitations:
- Local CLI commands operate on files and synthetic data unless the user provides live credentials.
- Paper/live workers use order-book polling or deterministic simulation rather than a full exchange event stream.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click
import pandas as pd

from analysis.comparator import compare_runs
from analysis.reporter import write_html_report, write_json_report
from backtest.correctness_checker import CorrectnessChecker
from config.settings import Settings
from core.backtest_engine import BacktestConfig, BacktestEngine
from core.client import NobitexClient
from core.cost_engine import CostEngine
from core.data_manager import DataManager
from core.execution_calibrator import ExecutionCalibrator
from core.execution_profile import ExecutionProfile
from live.live_trader import LiveTradingEngine
from live.order_manager import TradingOrderManager
from live.paper_trader import PaperTradingEngine
from live.risk_manager import TradingRiskManager
from live.session_manager import SessionManager
from live.websocket_client import WebSocketPriceFeed
from strategies.base.strategy_interface import BaseStrategy
from strategies.base.validation import validate_strategy_file
from strategies.builtin.ma_crossover import MACrossoverStrategy
from strategies.builtin.rsi_strategy import RSIStrategy


REPORTS_DIR = Path("reports")
PAPER_ROOT = REPORTS_DIR / "paper_trading"
LIVE_ROOT = REPORTS_DIR / "live_trading"
PROFILE_ROOT = REPORTS_DIR / "execution_profiles"


class _SimulatedExecutionClient:
    """Safe execution client used for test-mode live trading sessions."""

    def __init__(self) -> None:
        self.order_id = 0

    def place_order(self, payload: dict[str, object]) -> dict[str, object]:
        self.order_id += 1
        return {"order_id": f"sim-{self.order_id}", "status": "filled", **payload}

    def cancel_order(self, payload: dict[str, object]) -> dict[str, object]:
        return {"status": "canceled", **payload}

    def get_orderbook(self, symbol: str) -> dict[str, object]:
        return {"symbol": symbol, "bids": [[100.0, 1.0]], "asks": [[100.1, 1.0]]}


def _load_strategy(name: str):
    builtins = {
        "MACrossoverStrategy": MACrossoverStrategy,
        "RSIStrategy": RSIStrategy,
    }
    if name in builtins:
        return builtins[name]()
    module = importlib.import_module(f"strategies.user.{name}")
    for value in module.__dict__.values():
        if isinstance(value, type) and issubclass(value, BaseStrategy) and value is not BaseStrategy:
            return value()
    raise click.ClickException(f"Strategy {name} not found")


def _load_frame(csv_path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(csv_path, parse_dates=["timestamp"], index_col="timestamp")
    if frame.index.tz is None:
        frame.index = frame.index.tz_localize("UTC")
    return frame


def _utc_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _spawn_worker(worker: str, session_id: str) -> int:
    command = [sys.executable, str(Path(__file__).resolve()), worker, "--session-id", session_id]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return int(process.pid)


def _load_execution_profile(path: str | None) -> ExecutionProfile | None:
    if not path:
        return None
    return ExecutionProfile.load(path)


@click.group()
def cli() -> None:
    """Quant system CLI."""


@cli.group()
def test() -> None:
    """Testing commands."""


@test.command("correctness")
def test_correctness() -> None:
    click.echo(json.dumps(CorrectnessChecker().run(), indent=2, default=str))


@test.command("all")
@click.option("--coverage", is_flag=True, default=False)
@click.option("--html", "html_report", is_flag=True, default=False)
def test_all(coverage: bool, html_report: bool) -> None:
    message = {"coverage_requested": coverage, "html_requested": html_report, "hint": "Run pytest --cov --cov-report=html"}
    click.echo(json.dumps(message, indent=2))


@cli.group("data")
def data_group() -> None:
    """Historical market data commands."""


@data_group.command("fetch")
@click.option("--symbol", required=True)
@click.option("--timeframe", required=True, help="Nobitex resolution such as 15, 60, D")
@click.option("--months", type=int, default=None, help="Look back this many 30-day months from now")
@click.option("--days", type=int, default=None, help="Look back this many days from now")
@click.option("--start", "start_text", default=None, help="UTC start time, e.g. 2025-01-01T00:00:00Z")
@click.option("--end", "end_text", default=None, help="UTC end time, defaults to now")
@click.option("--use-cache/--refresh", default=False, help="Reuse the range-specific CSV when it exists")
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite the target CSV if it already exists")
def fetch_data(
    symbol: str,
    timeframe: str,
    months: int | None,
    days: int | None,
    start_text: str | None,
    end_text: str | None,
    use_cache: bool,
    overwrite: bool,
) -> None:
    if months is not None and days is not None:
        raise click.ClickException("Use either --months or --days, not both")
    if (months is not None or days is not None) and start_text is not None:
        raise click.ClickException("Use either lookback options or --start, not both")

    end_dt = _utc_datetime(end_text) if end_text else datetime.now(timezone.utc)
    if start_text is not None:
        start_dt = _utc_datetime(start_text)
    elif months is not None:
        start_dt = end_dt - timedelta(days=30 * months)
    elif days is not None:
        start_dt = end_dt - timedelta(days=days)
    else:
        start_dt = end_dt - timedelta(days=30)
    if start_dt >= end_dt:
        raise click.ClickException("start must be earlier than end")

    manager = DataManager()
    path = manager.ranged_cache_path(symbol, timeframe, start_dt, end_dt)
    if path.exists():
        if use_cache:
            frame = pd.read_csv(path, parse_dates=["timestamp"], index_col="timestamp")
            used_cache = True
        elif overwrite:
            frame = manager.fetch_history(symbol=symbol, timeframe=timeframe, start=int(start_dt.timestamp()), end=int(end_dt.timestamp()), use_cache=False)
            manager.save_to_path(frame, path)
            used_cache = False
        else:
            raise click.ClickException(f"Target file already exists: {path}. Use --use-cache or --overwrite.")
    else:
        frame = manager.fetch_history(symbol=symbol, timeframe=timeframe, start=int(start_dt.timestamp()), end=int(end_dt.timestamp()), use_cache=False)
        manager.save_to_path(frame, path)
        used_cache = False

    click.echo(json.dumps({
        "symbol": symbol,
        "timeframe": timeframe,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "rows": int(len(frame)),
        "path": str(path),
        "used_cache": used_cache,
    }, indent=2))


@cli.group("calibrate")
def calibrate_group() -> None:
    """Execution calibration commands."""


@calibrate_group.command("execution")
@click.option("--symbol", required=True)
@click.option("--samples", type=int, default=5)
@click.option("--output", type=click.Path(path_type=Path), default=None)
def calibrate_execution(symbol: str, samples: int, output: Path | None) -> None:
    settings = Settings()
    profile = ExecutionCalibrator(NobitexClient(settings)).calibrate(symbol, snapshots=samples)
    output = output or (PROFILE_ROOT / f"{symbol.lower()}_latest.json")
    profile.save(output)
    click.echo(json.dumps({**profile.to_dict(), "profile_hash": profile.profile_hash(), "path": str(output)}, indent=2, default=str))


@cli.command()
@click.option("--strategy", "strategy_name", required=True)
@click.option("--symbol", required=True)
@click.option("--data-file", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--capital", default=10_000_000, type=float)
@click.option("--execution", default="next_open")
@click.option("--seed", default=42, type=int)
@click.option("--execution-mode", type=click.Choice(["static", "calibrated"]), default="static")
@click.option("--execution-profile", type=click.Path(exists=True, path_type=Path), default=None)
def backtest(strategy_name: str, symbol: str, data_file: Path, capital: float, execution: str, seed: int, execution_mode: str, execution_profile: Path | None) -> None:
    frame = _load_frame(data_file)
    strategy = _load_strategy(strategy_name)
    profile = _load_execution_profile(str(execution_profile) if execution_profile else None)
    config = BacktestConfig(initial_capital=capital, execution_model=execution, random_seed=seed, execution_mode=execution_mode)
    if profile is not None:
        config.commission_rate = profile.commission_rate
        config.spread_bps = profile.spread_bps
        config.slippage_bps = profile.slippage_bps
        config.execution_mode = profile.mode
        config.execution_profile_path = str(execution_profile)
        config.execution_profile_hash = profile.profile_hash()
    result = BacktestEngine(config).run(frame, strategy, symbol)
    payload = {"metrics": result.metrics, "trust": result.trust, "trades": result.trades}
    write_json_report("reports/latest_backtest.json", payload)
    write_html_report("reports/latest_backtest.html", payload)
    click.echo(json.dumps(payload, indent=2, default=str))


@cli.group("strategy")
def strategy_group() -> None:
    """Strategy utilities."""


@strategy_group.command("validate")
@click.option("--file", "file_path", required=True, type=click.Path(exists=True, path_type=Path))
def validate_strategy(file_path: Path) -> None:
    click.echo(json.dumps(validate_strategy_file(file_path), indent=2, default=str))


@cli.command("compare-runs")
@click.option("--run1", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--run2", required=True, type=click.Path(exists=True, path_type=Path))
def compare_runs_command(run1: Path, run2: Path) -> None:
    first = json.loads(run1.read_text(encoding="utf-8"))
    second = json.loads(run2.read_text(encoding="utf-8"))
    click.echo(json.dumps(compare_runs(first, second), indent=2))


@cli.group("paper")
def paper_group() -> None:
    """Paper trading commands."""


@paper_group.command("start")
@click.option("--strategy", "strategy_name", required=True)
@click.option("--symbol", required=True)
@click.option("--capital", type=float, default=None)
@click.option("--interval-seconds", type=float, default=5.0)
@click.option("--max-ticks", type=int, default=120)
@click.option("--data-file", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--simulated/--market", default=True)
def paper_start(strategy_name: str, symbol: str, capital: float | None, interval_seconds: float, max_ticks: int, data_file: Path | None, simulated: bool) -> None:
    settings = Settings()
    manager = SessionManager(PAPER_ROOT)
    capital = capital or settings.paper_capital
    record = manager.create("paper", strategy_name, symbol, capital, {"interval_seconds": interval_seconds, "max_ticks": max_ticks, "data_file": None if data_file is None else str(data_file), "simulated": simulated})
    pid = _spawn_worker("_paper-worker", record.session_id)
    record = manager.update(record.session_id, pid=pid)
    click.echo(json.dumps(record.to_dict(), indent=2))


@paper_group.command("stop")
@click.option("--session-id", required=True)
def paper_stop(session_id: str) -> None:
    manager = SessionManager(PAPER_ROOT)
    manager.request_stop(session_id)
    record = manager.update(session_id, status="stopping")
    click.echo(json.dumps(record.to_dict(), indent=2))


@paper_group.command("list")
def paper_list() -> None:
    manager = SessionManager(PAPER_ROOT)
    click.echo(json.dumps([record.to_dict() for record in manager.list()], indent=2))


@paper_group.command("report")
@click.option("--session-id", required=True)
def paper_report(session_id: str) -> None:
    manager = SessionManager(PAPER_ROOT)
    record = manager.get(session_id)
    if not record.report_path:
        raise click.ClickException("No paper trading report available yet")
    click.echo(Path(record.report_path).read_text(encoding="utf-8"))


@cli.group("live")
def live_group() -> None:
    """Live trading commands."""


@live_group.command("start")
@click.option("--strategy", "strategy_name", required=True)
@click.option("--symbol", required=True)
@click.option("--capital", type=float, default=10_000.0)
@click.option("--risk", type=float, default=None)
@click.option("--interval-seconds", type=float, default=5.0)
@click.option("--max-ticks", type=int, default=120)
@click.option("--test-mode/--real", default=True)
def live_start(strategy_name: str, symbol: str, capital: float, risk: float | None, interval_seconds: float, max_ticks: int, test_mode: bool) -> None:
    settings = Settings()
    if not click.confirm("Start live trading? This can place real or testnet orders depending on your environment."):
        raise click.ClickException("Live trading start cancelled")
    risk = risk or settings.live_risk_per_trade
    manager = SessionManager(LIVE_ROOT)
    record = manager.create("live", strategy_name, symbol, capital, {"interval_seconds": interval_seconds, "max_ticks": max_ticks, "risk": risk, "test_mode": test_mode})
    pid = _spawn_worker("_live-worker", record.session_id)
    record = manager.update(record.session_id, pid=pid)
    click.echo(json.dumps(record.to_dict(), indent=2))


@live_group.command("stop")
@click.option("--emergency", is_flag=True, default=False)
def live_stop(emergency: bool) -> None:
    manager = SessionManager(LIVE_ROOT)
    active = manager.list(status="active")
    for record in active:
        manager.request_stop(record.session_id)
        manager.update(record.session_id, status="stopping" if emergency else "stopped")
    click.echo(json.dumps({"emergency": emergency, "stopped_sessions": [record.session_id for record in active]}, indent=2))


@live_group.command("status")
def live_status() -> None:
    manager = SessionManager(LIVE_ROOT)
    click.echo(json.dumps([record.to_dict() for record in manager.list()], indent=2))


@live_group.command("positions")
def live_positions() -> None:
    manager = SessionManager(LIVE_ROOT)
    positions: list[dict[str, object]] = []
    for record in manager.list():
        if record.report_path and Path(record.report_path).exists():
            payload = json.loads(Path(record.report_path).read_text(encoding="utf-8"))
            positions.append({"session_id": record.session_id, "symbol": record.symbol, "open_position": payload.get("open_position", 0.0)})
    click.echo(json.dumps(positions, indent=2))


@cli.command("_paper-worker", hidden=True)
@click.option("--session-id", required=True)
def paper_worker(session_id: str) -> None:
    settings = Settings()
    manager = SessionManager(PAPER_ROOT)
    record = manager.get(session_id)
    feed = WebSocketPriceFeed(seed=settings.random_seed)
    strategy = _load_strategy(record.strategy)
    risk_manager = TradingRiskManager(record.capital, settings.live_max_position_size, settings.live_max_daily_loss, settings.live_risk_per_trade)
    engine = PaperTradingEngine(
        strategy=strategy,
        symbol=record.symbol,
        capital=record.capital,
        cost_engine=CostEngine(settings.paper_fee_rate, settings.spread_bps, settings.slippage_bps, seed=settings.random_seed),
        risk_manager=risk_manager,
        report_dir=PAPER_ROOT,
    )
    stop_path = manager.stop_flag(session_id)
    manager.clear_stop(session_id)
    for tick in feed.iter_ticks(record.symbol, stop_path=stop_path, interval_seconds=record.config.get("interval_seconds", settings.market_data_poll_seconds), max_ticks=record.config.get("max_ticks"), simulated=record.config.get("simulated", True), data_file=record.config.get("data_file")):
        timestamp = str(tick.timestamp)
        engine.on_tick(timestamp=timestamp, price=float(tick.price), volume=float(tick.volume))
    report_path = engine.report(session_id)
    manager.update(session_id, status="stopped", report_path=str(report_path), pid=None)


@cli.command("_live-worker", hidden=True)
@click.option("--session-id", required=True)
def live_worker(session_id: str) -> None:
    settings = Settings()
    manager = SessionManager(LIVE_ROOT)
    record = manager.get(session_id)
    client = _SimulatedExecutionClient() if record.config.get("test_mode", True) else NobitexClient(settings)
    feed = WebSocketPriceFeed(client=None if record.config.get("test_mode", True) else client, seed=settings.random_seed)
    strategy = _load_strategy(record.strategy)
    order_manager = TradingOrderManager(client)
    risk_manager = TradingRiskManager(record.capital, settings.live_max_position_size, settings.live_max_daily_loss, record.config.get("risk", settings.live_risk_per_trade))
    engine = LiveTradingEngine(strategy=strategy, symbol=record.symbol, capital=record.capital, order_manager=order_manager, risk_manager=risk_manager, report_dir=LIVE_ROOT)
    stop_path = manager.stop_flag(session_id)
    manager.clear_stop(session_id)
    for tick in feed.iter_ticks(record.symbol, stop_path=stop_path, interval_seconds=record.config.get("interval_seconds", settings.market_data_poll_seconds), max_ticks=record.config.get("max_ticks"), simulated=record.config.get("test_mode", True)):
        engine.on_tick(timestamp=str(tick.timestamp), price=float(tick.price), volume=float(tick.volume))
    engine.emergency_stop()
    report_path = engine.report(session_id)
    manager.update(session_id, status="stopped", report_path=str(report_path), pid=None)


if __name__ == "__main__":
    cli()
