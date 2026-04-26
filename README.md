# Nobitex Quant System

Nobitex Quant System is a standalone Python trading research project for Nobitex with three main goals:

- keep the core trading engine separate from user strategy code
- produce deterministic, trustable backtest results
- enforce a strong testing and validation workflow for both built-in and user strategies

The project is organized so users only need to add or edit files inside `strategies/user/` when creating new strategies. Core execution, cost modeling, reporting, validation, and live/paper trading helpers remain isolated in their own packages.

If another AI agent or coding assistant will work on this repository, start with:

- `docs/AI_AGENT_ONBOARDING.md`
- `strategies/user/AI_GUIDE.md`
- `strategies/user/AI_CHECKLIST.md`

## Highlights

- Deterministic backtesting with a configurable random seed
- No-lookahead strategy execution model using historical slices only
- Cost modeling for commission, spread, and slippage in both `static` and `calibrated` execution modes
- Strategy validation tools for inheritance, indicator shape/alignment, deterministic replay, reset safety, and anti-lookahead checks
- Built-in sample strategies for moving-average crossover and RSI
- Paper trading and live trading session commands with audit reporting and emergency-stop support
- CLI commands for correctness checks, data download, calibration, backtests, strategy validation, and run comparison
- Unit, integration, property-based, and strategy validation tests

## Project layout

```text
.
├── analysis/      # reports, summaries, comparators, visualization payloads
├── backtest/      # metrics, optimization helpers, walk-forward, correctness checks
├── config/        # runtime settings and risk profile definitions
├── core/          # client, data manager, cost engine, order manager, backtest engine
├── docs/          # trust, testing, API, configuration, and strategy docs
├── live/          # paper trading, live execution, session, and market-feed helpers
├── strategies/
│   ├── base/      # BaseStrategy, Signal, context, validation helpers
│   ├── builtin/   # reference strategies
│   └── user/      # add your custom strategies here
└── tests/         # unit, integration, property, and strategy tests
```

## How the system is split

The repository is intentionally divided into layers with different responsibilities:

- `strategies/user/` is the user-editable area for custom trading logic
- `strategies/base/` defines the strategy contract, context, signals, and validation helpers
- `core/` contains execution primitives such as the backtest engine and cost model
- `backtest/` contains reporting-oriented helpers such as metrics, correctness checks, and walk-forward utilities
- `live/` contains paper/live scaffolding and should not be treated as equivalent to the research backtester
- `live/` reuses strategy signals but maintains separate session state, audit logs, and risk controls for paper/live trading

This separation matters for trust: strategy code should express decision logic, while execution, fills, costs, and validation live in the framework.

## Installation

Create a virtual environment, activate it, and install the project requirements.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev] --break-system-packages
```

If your environment uses a package mirror, you can point `pip` at that mirror during installation:

```bash
pip install --index-url https://mirror-pypi.runflare.com/simple -e .[dev]
```
or
```bash
pip install -e .[dev] --break-system-packages
```
## Quick start

Run the full test suite with coverage:

```bash
pytest --cov
```

Run the built-in correctness check for the backtest engine:

```bash
quant test correctness
```

Validate a user strategy file:

```bash
quant strategy validate --file strategies/user/my_strategy.py
```

Run a sample backtest:

```bash
quant backtest \
  --strategy MACrossoverStrategy \
  --symbol BTCIRT \
  --data-file data/btcirt_1h.csv
```

Download market data from Nobitex:

```bash
quant data fetch \
  --symbol BTCIRT \
  --timeframe 15 \
  --months 3
```

Start a paper trading session:

```bash
quant paper start --strategy MACrossoverStrategy --symbol BTCIRT --capital 10000
```

Start a live trading session on test mode:

```bash
quant live start --strategy MACrossoverStrategy --symbol BTCIRT --capital 10000 --risk 0.01 --test-mode
```

## Backtest example

The CLI backtester expects a CSV file with a `timestamp` column and standard OHLCV columns:

- `timestamp`
- `open`
- `high`
- `low`
- `close`
- `volume`

Example input file:

```csv
timestamp,open,high,low,close,volume
2024-01-01T00:00:00Z,100,101,99,100.5,1200
2024-01-01T01:00:00Z,100.5,102,100,101.7,1500
2024-01-01T02:00:00Z,101.7,103,101.5,102.4,1300
```

Run a backtest with the built-in moving average crossover strategy:

```bash
quant backtest \
  --strategy MACrossoverStrategy \
  --symbol BTCIRT \
  --data-file data/btcirt_1h.csv \
  --capital 10000000 \
  --execution next_open \
  --seed 42
```

This command writes output reports to:

- `reports/latest_backtest.json`
- `reports/latest_backtest.html`

The report includes:

- top-level performance metrics
- trade list output
- trust and correctness metadata
- reproducibility hash for the generated trades

## Documentation map

Use this section as the primary index for the repository documentation.

Core project and trust docs:

- `docs/AI_AGENT_ONBOARDING.md` - short read-first brief for future AI agents
- `docs/trust_backtesting.md` - trust model, deterministic execution assumptions, and signal metadata behavior
- `docs/testing_guide.md` - what correctness-critical tests should cover
- `docs/live_trading.md` - setup, commands, and safety notes for paper/live trading
- `docs/configuration.md` - environment variables and reproducibility-sensitive settings
- `docs/api/nobitex_reference.md` - Nobitex endpoint summary used by the client

Strategy development docs:

- `docs/strategy_development/writing_strategies.md` - strategy authoring rules and supported metadata
- `docs/strategy_development/validation_process.md` - what `quant strategy validate` checks
- `strategies/user/AI_GUIDE.md` - practical instructions for AI-written strategies
- `strategies/user/AI_CHECKLIST.md` - review checklist before accepting a strategy
- `strategies/user/example_ai_strategy.py` - minimal example strategy

Implementation areas worth reading together with the docs:

- `core/backtest_engine.py` - execution model, position lifecycle, and trust payload
- `core/cost_engine.py` - commission, spread, and slippage modeling
- `core/data_manager.py` - historical data download and local CSV caching
- `core/execution_profile.py` - static vs calibrated execution profile schema
- `core/execution_calibrator.py` - order-book-based calibration helpers
- `strategies/base/validation.py` - strategy validation and replay checks
- `backtest/correctness_checker.py` - known-result correctness scenarios

## Writing a user strategy

User strategies belong in `strategies/user/` and should inherit from `BaseStrategy`.

If another AI agent will be writing strategies in this repo, point it to:

- `strategies/user/AI_GUIDE.md`
- `strategies/user/AI_CHECKLIST.md`
- `strategies/user/example_ai_strategy.py`

Minimal example:

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

        if context.history["close"].iloc[-1] > context.history["close"].iloc[-2]:
            return Signal(
                timestamp=context.data.index[context.current_index],
                symbol=context.symbol,
                action="buy",
            )
        return None
```

Save that file as `strategies/user/MyMomentumStrategy.py`, then validate it:

```bash
quant strategy validate --file strategies/user/MyMomentumStrategy.py
```

If the strategy keeps mutable state between bars, implement `reset()` so a new backtest or validation run starts from a clean state.

Optional signal metadata supported by the backtest engine:

- `quantity`: explicit position size instead of default all-in sizing
- `execution_price`: explicit fill price for strategy-managed pending/exit logic
- `engine_managed_exits`: set to `False` when the strategy emits its own exit signals and prices
- `exit_reason`: recorded on the trade when the signal closes an existing position

Practical strategy constraints:

- strategies should decide from `context.history`
- strategies should not maintain hidden state unless they can fully restore it in `reset()`
- strategies should not assume multiple concurrent engine positions unless the framework is extended for that
- strategies should keep indicator lengths and indexes aligned with the input dataframe
- strategies should be instantiable without required constructor arguments so validation can construct them safely

## Trust and correctness model

This project is designed around reproducible research rather than optimistic simulation.

- Strategies receive `context.history`, not future rows
- Signals are generated per bar and executed using the configured execution model unless a strategy explicitly supplies `execution_price`
- Costs are applied through `core/cost_engine.py`
- Backtests can use either `static` configured costs or a saved `calibrated` execution profile
- Backtest output includes seed, execution model, cost breakdown, and reproducibility hash
- The engine resets each strategy before every run so reused strategy instances remain reproducible
- `backtest/correctness_checker.py` verifies known-result scenarios such as buy-and-hold and cost drag

The most important correctness assumptions are:

- identical inputs and seed should produce identical trades and metrics
- strategy replay should remain stable after `reset()`
- future-data mutation should not change historical decisions
- execution costs should be applied consistently on entry and exit
- live execution helpers should remain conceptually separate from research/backtest logic
- paper/live trading should never change historical backtest results for the same seed and inputs

For more detail, see:

- `docs/AI_AGENT_ONBOARDING.md`
- `docs/trust_backtesting.md`
- `docs/testing_guide.md`
- `docs/configuration.md`
- `docs/api/nobitex_reference.md`
- `docs/strategy_development/writing_strategies.md`
- `docs/strategy_development/validation_process.md`
- `strategies/user/AI_GUIDE.md`
- `strategies/user/AI_CHECKLIST.md`

## Useful commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run correctness checks
quant test correctness

# Calibrate execution costs from live order books
quant calibrate execution --symbol BTCIRT --samples 5

# Validate a strategy
quant strategy validate --file strategies/user/my_strategy.py

# Compare two backtest reports
quant compare-runs --run1 reports/run1.json --run2 reports/run2.json

# Start paper trading
quant paper start --strategy MACrossoverStrategy --symbol BTCIRT --capital 10000

# Stop a paper trading session
quant paper stop --session-id <id>

# Start live trading
quant live start --strategy MACrossoverStrategy --symbol BTCIRT --capital 10000 --risk 0.01 --test-mode

# Emergency stop live trading
quant live stop --emergency
```

## Configuration

Runtime settings are loaded from `.env` using the `NOBITEX_` prefix.

Start from the example file:

```bash
cp .env.example .env
```

Then set your Nobitex token in `.env`:

```env
NOBITEX_ENV=prod
NOBITEX_API_TOKEN=your_token_here
```

Important settings include:

- `NOBITEX_ENV`
- `NOBITEX_API_TOKEN`
- `NOBITEX_COMMISSION_RATE`
- `NOBITEX_SPREAD_BPS`
- `NOBITEX_SLIPPAGE_BPS`
- `NOBITEX_RANDOM_SEED`
- `NOBITEX_EXECUTION_MODEL`
- `NOBITEX_EXECUTION_MODE`
- `NOBITEX_EXECUTION_PROFILE_PATH`
- `NOBITEX_MAX_POSITIONS`
- `NOBITEX_ALLOW_SHORTING`
- `NOBITEX_PAPER_CAPITAL`
- `NOBITEX_PAPER_FEE_RATE`
- `NOBITEX_LIVE_API_KEY`
- `NOBITEX_LIVE_API_SECRET`
- `NOBITEX_LIVE_MAX_POSITION_SIZE`
- `NOBITEX_LIVE_MAX_DAILY_LOSS`
- `NOBITEX_LIVE_RISK_PER_TRADE`
- `NOBITEX_WEBSOCKET_URL`
- `NOBITEX_MARKET_DATA_POLL_SECONDS`

See `docs/configuration.md` for the full configuration reference.

## Downloading historical data

The CLI provides a data download command backed by `core/data_manager.py`.

Fetch the last 3 months of BTCIRT 15-minute candles:

```bash
quant data fetch \
  --symbol BTCIRT \
  --timeframe 15 \
  --months 3
```

This writes a range-specific CSV under `data/`, for example:

```text
data/btcirt_15m_2026-01-19_2026-04-19.csv
```

Useful options:

- `--months 3` for a 3 x 30-day lookback
- `--days 7` for a day-based lookback
- `--start 2025-01-01T00:00:00Z --end 2025-03-31T23:59:59Z` for an explicit UTC range
- `--use-cache` to reuse an existing range-specific CSV
- `--overwrite` to replace an existing range-specific CSV
- `--refresh` to force a fresh download when the target file does not already exist

If the target CSV already exists, the command now refuses to overwrite it unless you pass either `--use-cache` or `--overwrite`.

Example explicit date range:

```bash
quant data fetch \
  --symbol BTCIRT \
  --timeframe 15 \
  --start 2025-01-01T00:00:00Z \
  --end 2025-03-31T23:59:59Z \
  --overwrite
```

Use the downloaded file in a backtest:

```bash
quant backtest \
  --strategy MACrossoverStrategy \
  --symbol BTCIRT \
  --data-file data/btcirt_15m_2026-01-19_2026-04-19.csv
```

One-line example:

```bash
quant backtest --strategy BuyAndHoldPAXGIRT --symbol PAXGIRT --data-file data/paxgirt_15m_2026-01-19_2026-04-19.csv --capital 1000000 --execution next_open --seed 42
```

## Static vs calibrated execution costs

Use `static` mode for simple research with fixed assumptions:

```bash
quant backtest \
  --strategy MACrossoverStrategy \
  --symbol BTCIRT \
  --data-file data/btcirt_15m_2026-01-19_2026-04-19.csv \
  --execution-mode static
```

Build a calibrated execution profile from live order books:

```bash
quant calibrate execution --symbol BTCIRT --samples 5 --output reports/execution_profiles/btcirt_latest.json
```

Then use it in a realism-sensitive backtest:

```bash
quant backtest \
  --strategy MACrossoverStrategy \
  --symbol BTCIRT \
  --data-file data/btcirt_15m_2026-01-19_2026-04-19.csv \
  --execution-profile reports/execution_profiles/btcirt_latest.json
```

Calibrated mode does not change strategy logic. It only changes the execution-cost assumptions loaded into the backtest.

## Paper trading and live trading

Paper trading uses strategy signals with virtual capital and saves reports under `reports/paper_trading/`.

Start a paper session:

```bash
quant paper start --strategy MACrossoverStrategy --symbol BTCIRT --capital 10000
```

Stop it:

```bash
quant paper stop --session-id <id>
```

List sessions:

```bash
quant paper list
```

Read the report:

```bash
quant paper report --session-id <id>
```

Live trading uses the Nobitex API, account-level risk limits, and audit logs under `reports/live_trading/`.

Start live trading:

```bash
quant live start --strategy MACrossoverStrategy --symbol BTCIRT --capital 10000 --risk 0.01 --test-mode
```

Check status:

```bash
quant live status
```

Inspect open positions from saved reports:

```bash
quant live positions
```

Emergency stop all active live sessions:

```bash
quant live stop --emergency
```

Read `docs/live_trading.md` before using these commands.

## Notes and limitations

- The backtest engine supports one open engine-level position at a time
- Live and paper-trading helpers under `live/` are separate from research/backtest execution in `core/` and `backtest/`
- User strategies may express custom sizing and explicit fills through signal metadata, but portfolio/broker state still lives in the engine

## Testing and review expectations

When changing correctness-sensitive code, prefer to cover at least one of these:

- deterministic replay of the same strategy/data/seed
- anti-lookahead behavior under mutated future data
- strategy-state reset behavior across repeated runs
- cost-model behavior for commission, spread, and slippage
- CLI behavior matching the documented workflow

Relevant test areas:

- `tests/integration/` for end-to-end backtest and CLI behavior
- `tests/property/` for invariants
- `tests/strategies/` for validation and user-strategy regressions
- `tests/unit/` for focused component behavior
- `tests/unit/test_live.py` and `tests/integration/test_correctness_and_cli.py` for paper/live and CLI flows

## Recommended reading order

For a human or AI agent trying to understand the repo quickly:

1. `docs/AI_AGENT_ONBOARDING.md`
2. `README.md`
3. `docs/trust_backtesting.md`
4. `docs/testing_guide.md`
5. `docs/strategy_development/writing_strategies.md`
6. `docs/strategy_development/validation_process.md`
7. `core/backtest_engine.py`
8. `strategies/base/validation.py`
9. `docs/live_trading.md`

- The current implementation is focused on long-only, single-symbol backtesting
- Partial fills are not modeled
- WebSocket streaming is not implemented in the core API client yet
- The live engine is scaffolding-oriented and intended for controlled extension

If you want to extend the system, the safest workflow is:

1. add a strategy under `strategies/user/`
2. validate it with `quant strategy validate`
3. run `pytest --cov`
4. backtest it on a prepared CSV dataset
