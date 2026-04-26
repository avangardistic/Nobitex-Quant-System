import json
from pathlib import Path

from click.testing import CliRunner

from backtest.correctness_checker import CorrectnessChecker
from cli import cli


def test_correctness_checker():
    result = CorrectnessChecker().run()
    assert result["buy_hold_trade_count"] == 1
    assert result["commission_reduces_equity"] is True


def test_cli_commands(csv_data_file):
    runner = CliRunner()
    result = runner.invoke(cli, ["test", "correctness"])
    assert result.exit_code == 0
    backtest = runner.invoke(cli, ["backtest", "--strategy", "MACrossoverStrategy", "--symbol", "BTCIRT", "--data-file", str(csv_data_file)])
    assert backtest.exit_code == 0


def test_data_fetch_command_uses_data_manager(monkeypatch):
    class DummyManager:
        def fetch_history(self, symbol, timeframe, start, end, use_cache):
            self.called = {
                "symbol": symbol,
                "timeframe": timeframe,
                "start": start,
                "end": end,
                "use_cache": use_cache,
            }
            return [1, 2, 3]

        def ranged_cache_path(self, symbol, timeframe, start, end):
            return Path(f"data/{symbol.lower()}_{timeframe}m_{start:%Y-%m-%d}_{end:%Y-%m-%d}.csv")

        @staticmethod
        def save_to_path(frame, path):
            return path

    manager = DummyManager()
    monkeypatch.setattr("cli.DataManager", lambda: manager)

    runner = CliRunner()
    result = runner.invoke(cli, ["data", "fetch", "--symbol", "BTCIRT", "--timeframe", "15", "--months", "3"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["symbol"] == "BTCIRT"
    assert payload["timeframe"] == "15"
    assert payload["rows"] == 3
    assert payload["path"].startswith("data/btcirt_15m_")


def test_data_fetch_refuses_to_overwrite_existing_file(monkeypatch, tmp_path):
    class DummyManager:
        def ranged_cache_path(self, symbol, timeframe, start, end):
            path = tmp_path / "btcirt_15m_2026-01-19_2026-04-19.csv"
            path.write_text("timestamp,open,high,low,close,volume\n", encoding="utf-8")
            return path

    monkeypatch.setattr("cli.DataManager", lambda: DummyManager())

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["data", "fetch", "--symbol", "BTCIRT", "--timeframe", "15", "--start", "2026-01-19T00:00:00Z", "--end", "2026-04-19T00:00:00Z"],
    )

    assert result.exit_code != 0
    assert "already exists" in result.output


def test_calibrate_execution_command(monkeypatch, tmp_path):
    class DummyProfile:
        def to_dict(self):
            return {"symbol": "BTCIRT", "mode": "calibrated", "spread_bps": 4.0, "slippage_bps": 6.0}

        def profile_hash(self):
            return "hash"

        def save(self, path):
            Path(path).write_text("{}", encoding="utf-8")
            return path

    class DummyCalibrator:
        def __init__(self, client):
            self.client = client

        def calibrate(self, symbol, snapshots=5):
            assert symbol == "BTCIRT"
            assert snapshots == 3
            return DummyProfile()

    monkeypatch.setattr("cli.ExecutionCalibrator", DummyCalibrator)

    runner = CliRunner()
    result = runner.invoke(cli, ["calibrate", "execution", "--symbol", "BTCIRT", "--samples", "3", "--output", str(tmp_path / "profile.json")])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["symbol"] == "BTCIRT"
    assert payload["profile_hash"] == "hash"


def test_paper_and_live_start_commands(monkeypatch):
    monkeypatch.setattr("cli._spawn_worker", lambda worker, session_id: 12345)

    runner = CliRunner()
    paper = runner.invoke(cli, ["paper", "start", "--strategy", "MACrossoverStrategy", "--symbol", "BTCIRT", "--capital", "1000", "--max-ticks", "1"])
    assert paper.exit_code == 0
    live = runner.invoke(cli, ["live", "start", "--strategy", "MACrossoverStrategy", "--symbol", "BTCIRT", "--capital", "1000"], input="y\n")
    assert live.exit_code == 0
