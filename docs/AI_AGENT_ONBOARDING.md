# AI Agent Onboarding

Read this first before changing code in this repository.

## What this repo is

Nobitex Quant System is a Python quantitative research and backtesting framework for Nobitex. Its core goals are:

- keep core execution separate from user strategy code
- produce deterministic and reproducible backtest results
- validate user strategies for no-lookahead and reset-safe behavior

## Repository map

- `core/`: backtest engine, cost engine, client, data utilities, order/risk helpers
- `backtest/`: metrics, correctness checks, optimizer, walk-forward helpers
- `live/`: paper/live trading scaffolding; separate from research/backtest logic
- `strategies/base/`: `BaseStrategy`, `Signal`, `StrategyContext`, validation helpers
- `strategies/builtin/`: reference strategies
- `strategies/user/`: user-editable strategies and AI-facing strategy docs
- `tests/`: unit, integration, property, and strategy validation coverage

## Non-negotiable trust rules

- Strategy decisions must use `context.history`, not future rows
- Backtests must stay deterministic under the same seed, config, and input data
- If a strategy keeps mutable state, it must implement `reset()` so reruns are identical
- Indicator outputs must match input length and index alignment
- Do not assume multiple concurrent engine positions unless the engine is explicitly extended

## Backtest engine behavior you must know

- Default execution is next-bar open
- The engine resets the strategy before each run
- A strategy may optionally use `Signal.metadata` with:
  - `quantity`
  - `execution_price`
  - `engine_managed_exits`
  - `exit_reason`
- Engine costs are applied in `core/cost_engine.py`
- Backtests can run in `static` or `calibrated` execution mode

## If you are writing or editing a strategy

Read these files before touching `strategies/user/`:

- `strategies/user/AI_GUIDE.md`
- `strategies/user/AI_CHECKLIST.md`
- `docs/strategy_development/writing_strategies.md`
- `docs/strategy_development/validation_process.md`

## If you are auditing or changing engine behavior

Read these files first:

- `README.md`
- `docs/trust_backtesting.md`
- `docs/testing_guide.md`
- `docs/live_trading.md`
- `core/backtest_engine.py`
- `strategies/base/validation.py`

## Minimum workflow before you finish

1. Validate strategy changes with `quant strategy validate --file ...` when relevant
2. Run targeted tests or `pytest`
3. Make sure docs still match the implemented behavior
4. Call out any assumptions, testing gaps, or trust-model risks in your final note

## Things that often go wrong

- hidden strategy state not cleared in `reset()`
- indicator series with wrong index alignment
- accidental future-data access via `context.data`
- strategy sizing intent not matching engine execution behavior
- docs describing an older behavior than the current code
