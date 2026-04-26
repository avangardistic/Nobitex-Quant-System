# Testing Guide

Run the full suite with `pytest --cov`. Use `quant test correctness` for a fast correctness check of the backtest engine.

Correctness-critical coverage should include:

- deterministic replay under a fixed seed
- reused strategy instances producing identical results because `reset()` is called
- no-lookahead behavior under mutated future data
- signal metadata behavior such as explicit `quantity` and `execution_price`
- user-strategy validation failures for hidden mutable state and malformed indicator outputs
- execution-profile calibration or loading behavior for backtests
- paper/live session state, audit reports, and emergency-stop flows

Property tests validate invariants such as non-negative equity for long-only runs and deterministic results under a fixed seed.
