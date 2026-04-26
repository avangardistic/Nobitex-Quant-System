# Trustable Backtesting

The backtest engine processes bars one at a time and passes only `history = data.iloc[:i]` to strategies. Signals emitted on bar `i` are executed on bar `i+1` open by default. This prevents lookahead bias.

Each run calls `strategy.reset()` first so a reused strategy instance starts from clean state. This matters for strategies that keep cooldowns, pending orders, or cached signals on `self`.

Strategies may optionally provide execution hints via `Signal.metadata`:

- `quantity`: explicit size for the opened position
- `execution_price`: explicit fill price for strategy-managed entry or exit logic
- `engine_managed_exits=False`: disables engine-side TP/SL/trailing handling for that position so the strategy can emit its own exit signal
- `exit_reason`: stored on the trade when the signal closes an existing position

Backtests now support two cost modes:

- `static`: use configured commission/spread/slippage assumptions
- `calibrated`: load a saved execution profile built from observed order book snapshots

Costs use a deterministic `CostEngine` seeded from config. The report includes the seed, execution model, execution mode, total commission, spread, slippage, and a reproducibility hash of the trade list.
