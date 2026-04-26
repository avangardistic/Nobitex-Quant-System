# AI Strategy Review Checklist

Use this checklist before considering a new strategy ready.

## File placement

- [ ] The strategy file lives in `strategies/user/`
- [ ] No core or framework files were modified unnecessarily

## Interface compliance

- [ ] The class inherits from `BaseStrategy`
- [ ] The strategy can be instantiated without required constructor arguments
- [ ] `calculate_indicators` is implemented
- [ ] `generate_signal` is implemented
- [ ] The strategy defines a clear `name`
- [ ] If the strategy is stateful, `reset()` restores the initial state

## Data safety

- [ ] Trading logic uses `context.history`
- [ ] No future rows are accessed
- [ ] Warm-up handling exists for short history
- [ ] Indicator calculations do not leak future data

## Output correctness

- [ ] `calculate_indicators` returns `dict[str, pd.Series]`
- [ ] Indicator series lengths match the input dataframe length
- [ ] Indicator series indexes match the input dataframe index
- [ ] `generate_signal` returns `Signal` or `None`
- [ ] Signal actions are valid, such as `buy` or `sell`
- [ ] Any use of `Signal.metadata` is limited to supported keys such as `quantity`, `execution_price`, `engine_managed_exits`, and `exit_reason`

## Code quality

- [ ] The strategy is deterministic
- [ ] Replaying the same data after `reset()` produces the same signals
- [ ] Parameters are readable and easy to tune
- [ ] The file contains only strategy logic
- [ ] The code is simple enough to audit

## Validation

- [ ] `quant strategy validate --file strategies/user/<file>.py` passes
- [ ] `pytest` passes after adding the strategy
- [ ] A sample backtest runs without runtime errors

## Final review

- [ ] The strategy objective is clearly described
- [ ] The logic is explainable in plain language
- [ ] The strategy does not assume unsupported platform behavior
- [ ] The strategy does not assume multiple concurrent engine positions unless the engine is explicitly extended
