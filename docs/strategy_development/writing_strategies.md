# Writing Strategies

Place user strategies in `strategies/user/`. Inherit from `BaseStrategy`, return aligned indicator series, and only use `context.history` when generating signals.

Checklist:
- Do not access `context.data.iloc[context.current_index + 1:]`
- Do not use unshifted future labels
- Return `Signal` or `None`
- Keep indicator indexes aligned with the input dataframe
- Keep logic deterministic for reproducibility
- If you keep mutable state on `self`, implement `reset()` so each run starts cleanly

The backtest engine supports these optional `Signal.metadata` keys for advanced strategies:

- `quantity` for explicit sizing
- `execution_price` for strategy-managed pending fills or exits
- `engine_managed_exits=False` when the strategy wants to manage exits itself
- `exit_reason` to label a signal-driven close

Strategies should still assume a single engine-level position unless the core engine is extended.
