# Nobitex Quant System

> A trust-first Python research and trading framework for **Nobitex** — built for reproducible backtests, validated strategy development, calibrated execution costs, and safe paper/live trading workflows.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Package](https://img.shields.io/badge/package-setuptools-7A4DFF)
![Tests](https://img.shields.io/badge/tests-pytest-0A7EA4)
![Trading](https://img.shields.io/badge/trading-research%20%7C%20paper%20%7C%20live-00A86B)

## Table of Contents

- [Why This Project Exists](#why-this-project-exists)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Market Data](#market-data)
- [Backtesting](#backtesting)
- [Strategy Development](#strategy-development)
- [Execution Cost Modeling](#execution-cost-modeling)
- [Paper Trading](#paper-trading)
- [Live Trading](#live-trading)
- [Configuration](#configuration)
- [Testing and Validation](#testing-and-validation)
- [Documentation Map](#documentation-map)
- [Notes and Limitations](#notes-and-limitations)

## Why This Project Exists

Most trading experiments fail because the research loop is not reproducible: future data leaks into decisions, execution costs are hand-waved, strategy state is not reset safely, and paper/live code quietly diverges from backtest assumptions.

Nobitex Quant System is designed around a stricter model:

- **Strategies decide only from historical slices** exposed through `context.history`.
- **Backtests are deterministic** for identical inputs, configuration, and random seed.
- **Costs are explicit** through commission, spread, and slippage models.
- **Strategy validation is first-class** before a strategy is trusted.
- **Research and live execution are separated** so operational code does not mutate historical assumptions.

The result is a compact framework for building, testing, comparing, and operating Nobitex strategies with a strong emphasis on correctness.

## Key Features

| Area | What You Get |
| --- | --- |
| Backtesting | Deterministic engine, configurable execution model, reproducibility hash, trade reports |
| Strategy Safety | Base strategy contract, reset checks, indicator alignment checks, anti-lookahead validation |
| Cost Modeling | Static and calibrated execution profiles with commission, spread, and slippage |
| Market Data | Nobitex historical candle download with local CSV caching |
| Reporting | JSON and HTML backtest reports, run comparison utilities, audit payloads |
| Paper Trading | Simulated sessions, saved reports, session start/stop/list/report commands |
| Live Trading | Test mode, risk limits, emergency stop, audit reports, Nobitex API integration |
| Testing | Unit, integration, property-based, correctness, and strategy validation tests |

## Architecture

```text
.
├── analysis/                 # Reports, summaries, run comparison helpers
├── backtest/                 # Metrics, correctness checks, optimization, walk-forward tools
├── config/                   # Runtime settings and risk profiles
├── core/                     # Backtest engine, data manager, client, costs, calibration
├── docs/                     # Trust, configuration, API, testing, and strategy guides
├── live/                     # Paper/live sessions, risk, order manager, market feed helpers
├── strategies/
│   ├── base/                 # BaseStrategy, Signal, context, validation helpers
│   ├── builtin/              # Reference strategies such as MA crossover and RSI
│   └── user/                 # Your custom strategies live here
├── tests/                    # Unit, integration, property, and strategy tests
├── cli.py                    # `quant` command-line interface
├── pyproject.toml            # Package metadata and dependencies
└── README.md
```

### Layer Responsibilities

- `strategies/user/` is the safe user-editable area for custom trading ideas.
- `strategies/base/` defines the public strategy contract and validation rules.
- `core/` owns execution-critical primitives such as fills, costs, data loading, and backtesting.
- `backtest/` provides correctness checks, metrics, optimization, and walk-forward helpers.
- `analysis/` turns runs into reports and comparison payloads.
- `live/` handles paper/live sessions, audit state, risk controls, and operational concerns.

This split keeps strategy code focused on decisions while the framework owns execution, accounting, reproducibility, and validation.

## Installation

### Requirements

- Python `3.11+`
- `pip`
- A virtual environment is recommended

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

If your environment requires system-package override flags:

```bash
pip install -e .[dev] --break-system-packages
```

If you use a PyPI mirror:

```bash
pip install --index-url https://mirror-pypi.runflare.com/simple -e .[dev]
```

Verify that the CLI is available:

```bash
quant --help
```

## Quick Start

Run the correctness checks:

```bash
quant test correctness
```

Run the full test suite:

```bash
pytest
```

Download recent BTC/IRT candles:

```bash
quant data fetch \
  --symbol BTCIRT \
  --timeframe 15 \
  --months 3
```

Run a deterministic backtest:

```bash
quant backtest \
  --strategy MACrossoverStrategy \
  --symbol BTCIRT \
  --data-file data/btcirt_15m_2026-01-19_2026-04-19.csv \
  --capital 10000000 \
  --execution next_open \
  --seed 42
```

Validate a custom strategy:

```bash
quant strategy validate --file strategies/user/my_strategy.py
```

Start a simulated paper session:

```bash
quant paper start \
  --strategy MACrossoverStrategy \
  --symbol BTCIRT \
  --capital 10000
```

Start a live session in safe test mode:

```bash
quant live start \
  --strategy MACrossoverStrategy \
  --symbol BTCIRT \
  --capital 10000 \
  --risk 0.01 \
  --test-mode
```

## Market Data

Historical data is downloaded through `core/data_manager.py` and written to `data/` as range-specific CSV files.

Fetch the last 30 days by default:

```bash
quant data fetch --symbol BTCIRT --timeframe 15
```

Fetch a fixed lookback window:

```bash
quant data fetch \
  --symbol BTCIRT \
  --timeframe 15 \
  --days 7
```

Fetch an explicit UTC range:

```bash
quant data fetch \
  --symbol BTCIRT \
  --timeframe 15 \
  --start 2025-01-01T00:00:00Z \
  --end 2025-03-31T23:59:59Z \
  --overwrite
```

Useful options:

- `--months 3` uses a 3 × 30-day lookback from now.
- `--days 7` uses a day-based lookback from now.
- `--start ... --end ...` uses an explicit UTC time range.
- `--use-cache` reuses the target CSV when it already exists.
- `--overwrite` replaces the existing target CSV.
- `--refresh` forces a fresh download when the target file does not exist.

Expected backtest CSV schema:

```csv
timestamp,open,high,low,close,volume
2024-01-01T00:00:00Z,100,101,99,100.5,1200
2024-01-01T01:00:00Z,100.5,102,100,101.7,1500
2024-01-01T02:00:00Z,101.7,103,101.5,102.4,1300
```

## Backtesting

Backtests run one strategy over one OHLCV dataset and produce both machine-readable and human-readable reports.

```bash
quant backtest \
  --strategy MACrossoverStrategy \
  --symbol BTCIRT \
  --data-file data/btcirt_15m_2026-01-19_2026-04-19.csv \
  --capital 10000000 \
  --execution next_open \
  --seed 42 \
  --execution-mode static
```

Generated reports:

- `reports/latest_backtest.json`
- `reports/latest_backtest.html`

Report payloads include:

- performance metrics
- executed trades
- cost breakdown
- execution settings
- trust metadata
- deterministic reproducibility hash

Compare two saved backtest reports:

```bash
quant compare-runs \
  --run1 reports/run1.json \
  --run2 reports/run2.json
```

## Strategy Development

Custom strategies belong in `strategies/user/` and should inherit from `BaseStrategy`.

```python
import pandas as pd

from strategies.base.context import StrategyContext
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy


class MyMomentumStrategy(BaseStrategy):
    name = "MyMomentumStrategy"

    def reset(self) -> None:
        pass

    def calculate_indicators(self, data: pd.DataFrame) -> dict[str, pd.Series]:
        return {"close": data["close"]}

    def generate_signal(self, context: StrategyContext) -> Signal | None:
        if len(context.history) < 2:
            return None

        current_close = context.history["close"].iloc[-1]
        previous_close = context.history["close"].iloc[-2]

        if current_close > previous_close:
            return Signal(
                timestamp=context.data.index[context.current_index],
                symbol=context.symbol,
                action="buy",
            )

        return None
```

Save it as `strategies/user/my_momentum.py`, then validate it:

```bash
quant strategy validate --file strategies/user/my_momentum.py
```

Run it by module name:

```bash
quant backtest \
  --strategy my_momentum \
  --symbol BTCIRT \
  --data-file data/btcirt_15m_2026-01-19_2026-04-19.csv
```

### Strategy Rules

- Use `context.history` for decisions; do not read future rows.
- Keep indicator indexes and lengths aligned with the input dataframe.
- Make the class instantiable without required constructor arguments.
- Implement `reset()` when using mutable state between bars.
- Avoid hidden state that cannot be fully restored before validation or replay.
- Assume one open engine-managed position unless the framework is extended.

### Optional Signal Metadata

- `quantity` sets explicit position size instead of default all-in sizing.
- `execution_price` sets an explicit strategy-managed fill price.
- `engine_managed_exits=False` lets the strategy manage its own exits.
- `exit_reason` records why a signal closed an existing position.

For AI-assisted strategy writing, start with:

- `strategies/user/AI_GUIDE.md`
- `strategies/user/AI_CHECKLIST.md`
- `strategies/user/example_ai_strategy.py`

## Execution Cost Modeling

The backtest engine supports two execution-cost modes.

### Static Mode

Use fixed settings for fast research and repeatable experiments:

```bash
quant backtest \
  --strategy MACrossoverStrategy \
  --symbol BTCIRT \
  --data-file data/btcirt_15m_2026-01-19_2026-04-19.csv \
  --execution-mode static
```

### Calibrated Mode

Build an execution profile from live order-book snapshots:

```bash
quant calibrate execution \
  --symbol BTCIRT \
  --samples 5 \
  --output reports/execution_profiles/btcirt_latest.json
```

Use the profile in a realism-sensitive backtest:

```bash
quant backtest \
  --strategy MACrossoverStrategy \
  --symbol BTCIRT \
  --data-file data/btcirt_15m_2026-01-19_2026-04-19.csv \
  --execution-profile reports/execution_profiles/btcirt_latest.json
```

Calibrated mode does not change strategy logic. It only changes the commission, spread, and slippage assumptions loaded into the backtest.

## Paper Trading

Paper trading reuses strategy signals with virtual capital and saves reports under `reports/paper_trading/`.

Start a session:

```bash
quant paper start \
  --strategy MACrossoverStrategy \
  --symbol BTCIRT \
  --capital 10000 \
  --interval-seconds 5 \
  --max-ticks 120
```

Use a local data file for deterministic simulation:

```bash
quant paper start \
  --strategy MACrossoverStrategy \
  --symbol BTCIRT \
  --data-file data/btcirt_15m_2026-01-19_2026-04-19.csv
```

Manage sessions:

```bash
quant paper list
quant paper report --session-id <id>
quant paper stop --session-id <id>
```

## Live Trading

Live trading uses Nobitex credentials, account-level risk controls, session state, and audit reports under `reports/live_trading/`.

Start in test mode first:

```bash
quant live start \
  --strategy MACrossoverStrategy \
  --symbol BTCIRT \
  --capital 10000 \
  --risk 0.01 \
  --test-mode
```

Operational commands:

```bash
quant live status
quant live positions
quant live stop --emergency
```

> [!WARNING]
> Read `docs/live_trading.md` before using real credentials. Live trading can place real orders when started with real mode and valid API credentials.

## Configuration

Runtime settings are loaded from `.env` with the `NOBITEX_` prefix.

Create a local environment file:

```bash
cp .env.example .env
```

Minimal Nobitex API configuration:

```env
NOBITEX_ENV=prod
NOBITEX_API_TOKEN=your_token_here
```

Important settings:

| Setting | Purpose |
| --- | --- |
| `NOBITEX_ENV` | Runtime environment name |
| `NOBITEX_API_TOKEN` | Nobitex API token for authenticated requests |
| `NOBITEX_COMMISSION_RATE` | Static commission assumption |
| `NOBITEX_SPREAD_BPS` | Static spread assumption in basis points |
| `NOBITEX_SLIPPAGE_BPS` | Static slippage assumption in basis points |
| `NOBITEX_RANDOM_SEED` | Default reproducibility seed |
| `NOBITEX_EXECUTION_MODEL` | Backtest execution timing model |
| `NOBITEX_EXECUTION_MODE` | `static` or `calibrated` cost mode |
| `NOBITEX_EXECUTION_PROFILE_PATH` | Saved calibrated profile path |
| `NOBITEX_MAX_POSITIONS` | Position limit |
| `NOBITEX_ALLOW_SHORTING` | Short-selling toggle |
| `NOBITEX_PAPER_CAPITAL` | Default paper trading capital |
| `NOBITEX_LIVE_MAX_POSITION_SIZE` | Live position size limit |
| `NOBITEX_LIVE_MAX_DAILY_LOSS` | Live daily loss limit |
| `NOBITEX_LIVE_RISK_PER_TRADE` | Live risk-per-trade default |
| `NOBITEX_WEBSOCKET_URL` | Market feed URL |
| `NOBITEX_MARKET_DATA_POLL_SECONDS` | Poll interval for market data helpers |

See `docs/configuration.md` for the full reference.

## Testing and Validation

Run all tests:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov
```

Run framework correctness scenarios:

```bash
quant test correctness
```

Validate a user strategy:

```bash
quant strategy validate --file strategies/user/my_strategy.py
```

Validation checks include:

- inheritance from `BaseStrategy`
- safe construction without required arguments
- indicator shape and index alignment
- deterministic replay behavior
- reset safety
- anti-lookahead behavior under future-data mutation

## Trust and Correctness Model

This repository prioritizes reproducible research over optimistic simulation.

- Strategies receive historical slices, not future bars.
- Signals are generated bar-by-bar and executed through the configured model.
- Costs are applied consistently on entries and exits.
- Strategy instances are reset before runs when supported.
- Backtest outputs include seed, cost settings, execution mode, and reproducibility metadata.
- Correctness checks cover known-result scenarios such as buy-and-hold and cost drag.
- Paper/live trading state is operationally separate from research backtests.

Core expectation: identical input data, strategy code, configuration, and seed should produce identical trades and metrics.

## Documentation Map

Start here if you are new to the project:

- `docs/AI_AGENT_ONBOARDING.md` — short onboarding brief for AI agents and future maintainers
- `docs/trust_backtesting.md` — trust model, execution assumptions, and signal metadata behavior
- `docs/testing_guide.md` — correctness-critical testing guidance
- `docs/configuration.md` — environment variables and reproducibility-sensitive settings
- `docs/live_trading.md` — paper/live trading setup, commands, and safety notes
- `docs/api/nobitex_reference.md` — Nobitex endpoint summary used by the client

Strategy development:

- `docs/strategy_development/writing_strategies.md` — strategy authoring rules
- `docs/strategy_development/validation_process.md` — validation workflow and checks
- `strategies/user/AI_GUIDE.md` — practical guide for AI-written strategies
- `strategies/user/AI_CHECKLIST.md` — review checklist before accepting a strategy
- `strategies/user/example_ai_strategy.py` — minimal example strategy

Implementation references:

- `core/backtest_engine.py` — execution model, positions, trust payload
- `core/cost_engine.py` — commission, spread, and slippage modeling
- `core/data_manager.py` — historical data download and local CSV caching
- `core/execution_profile.py` — static vs calibrated execution profile schema
- `core/execution_calibrator.py` — order-book-based calibration helpers
- `strategies/base/validation.py` — strategy validation and replay checks
- `backtest/correctness_checker.py` — known-result correctness scenarios

## Useful Commands

```bash
# CLI help
quant --help

# Correctness checks
quant test correctness

# Full test suite
pytest

# Coverage
pytest --cov

# Download data
quant data fetch --symbol BTCIRT --timeframe 15 --months 3

# Backtest built-in strategy
quant backtest --strategy MACrossoverStrategy --symbol BTCIRT --data-file data/btcirt_15m_2026-01-19_2026-04-19.csv

# Validate custom strategy
quant strategy validate --file strategies/user/my_strategy.py

# Compare reports
quant compare-runs --run1 reports/run1.json --run2 reports/run2.json

# Calibrate costs
quant calibrate execution --symbol BTCIRT --samples 5

# Paper trading
quant paper start --strategy MACrossoverStrategy --symbol BTCIRT --capital 10000

# Live test mode
quant live start --strategy MACrossoverStrategy --symbol BTCIRT --capital 10000 --risk 0.01 --test-mode

# Emergency live stop
quant live stop --emergency
```

## Notes and Limitations

- The backtest engine currently supports one open engine-level position at a time.
- Live and paper trading helpers are operational scaffolding, not a replacement for exchange-grade infrastructure.
- Calibrated execution profiles depend on sampled market conditions and should be refreshed for realism-sensitive studies.
- Historical performance does not guarantee future returns.
- Always start with `--test-mode` before using real credentials.

## Disclaimer

This project is for research and engineering workflows. It is not financial advice, and it does not guarantee profitable trading. Use real trading features only after reviewing the code, configuration, exchange behavior, and risk limits yourself.
