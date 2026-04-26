# Validation Process

`quant strategy validate --file strategies/user/my_strategy.py` loads the strategy and performs a correctness-oriented validation pass.

The validator currently checks:

- the module exposes a `BaseStrategy` subclass
- the strategy is instantiable without constructor arguments
- `calculate_indicators()` returns a dict of `pd.Series`
- each indicator has the same length and index as the input data
- `generate_signal()` returns `Signal` or `None`
- replayed outputs are stable after `reset()`
- identical fresh instances produce identical replayed outputs
- anti-lookahead heuristics pass when future-visible data is mutated

Validation is intended to reject obviously unsafe or non-reproducible user code, not to prove trading edge.
