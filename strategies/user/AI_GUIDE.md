# AI Strategy Authoring Guide

This file is for AI agents that need to create or modify trading strategies in this repository.

## Hard rules

- Only add or edit strategy files inside `strategies/user/`
- Do not modify files in `core/`, `backtest/`, `live/`, `analysis/`, or `strategies/base/`
- Keep strategy logic deterministic
- Do not use future data
- Return only `Signal` or `None` from `generate_signal`
- If the strategy stores mutable state, implement `reset()` and make reruns identical

## Required interface

Every strategy must:

1. inherit from `BaseStrategy`
2. be instantiable without required constructor arguments
3. implement `calculate_indicators(self, data: pd.DataFrame) -> dict[str, pd.Series]`
4. implement `generate_signal(self, context: StrategyContext) -> Signal | None`

If the strategy is stateful, also implement:

5. `reset(self) -> None`

Use these imports:

```python
import pandas as pd

from strategies.base.context import StrategyContext
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy
```

Optional indicator helpers are available in `strategies/base/indicators.py`.

## Data access rules

Inside `generate_signal`:

- use `context.history` for all decision making
- treat `context.data.index[context.current_index]` as the signal timestamp
- never read `context.data.iloc[context.current_index + 1 :]`
- do not shift labels backward in a way that leaks future information

Good:

```python
last_close = context.history["close"].iloc[-1]
prev_close = context.history["close"].iloc[-2]
```

Bad:

```python
next_close = context.data["close"].iloc[context.current_index + 1]
```

## Output rules

`calculate_indicators` must return a dictionary where:

- each value is a `pd.Series`
- each series has the same length as the input `data`
- series indexes align with the input dataframe

`generate_signal` must return:

- `Signal(..., action="buy")`
- `Signal(..., action="sell")`
- or `None`

Optional `Signal.metadata` keys supported by the engine:

- `quantity`: explicit position size
- `execution_price`: explicit fill price
- `engine_managed_exits`: set `False` if the strategy will emit its own exit signal and price
- `exit_reason`: close reason recorded in the trade log

## Recommended structure

Start from this template:

```python
import pandas as pd

from strategies.base.context import StrategyContext
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy


class MyStrategy(BaseStrategy):
    name = "MyStrategy"

    def reset(self) -> None:
        self._last_signal_bar = None

    def calculate_indicators(self, data: pd.DataFrame) -> dict[str, pd.Series]:
        return {
            "close": data["close"],
        }

    def generate_signal(self, context: StrategyContext) -> Signal | None:
        if len(context.history) < 2:
            return None

        timestamp = context.data.index[context.current_index]
        last_close = context.history["close"].iloc[-1]
        prev_close = context.history["close"].iloc[-2]

        if last_close > prev_close:
            return Signal(timestamp=timestamp, symbol=context.symbol, action="buy")

        if last_close < prev_close:
            return Signal(timestamp=timestamp, symbol=context.symbol, action="sell")

        return None
```

## Naming conventions

- Use one public strategy class per file
- Match the filename to the strategy purpose, for example `momentum_breakout.py`
- Use a clear class name, for example `MomentumBreakoutStrategy`
- Set the `name` attribute explicitly

## Design guidelines

- Prefer simple, explainable rules over opaque logic
- Avoid hidden state unless absolutely necessary
- Keep parameters easy to tune
- Use built-in indicators where possible
- Make warm-up conditions explicit, for example `if len(context.history) < 50: return None`
- If you use state, make `reset()` fully reconstruct the initial state
- Do not assume multiple simultaneous engine positions or internal portfolio accounting unless the framework explicitly supports it

## Safety checklist

Before finishing a strategy, verify:

- it imports only what it needs
- it does not access future bars
- it handles short history safely
- it returns valid `Signal` objects
- indicator outputs align with the input data length
- indicator indexes align with the input dataframe
- repeated replays after `reset()` produce identical signals
- it does not raise exceptions on normal OHLCV input

## Validation workflow

After creating a strategy file, run:

```bash
quant strategy validate --file strategies/user/my_strategy.py
```

Then run the test suite:

```bash
pytest
```

If you have a prepared CSV dataset, run a backtest:

```bash
quant backtest \
  --strategy MyStrategyModuleName \
  --symbol BTCIRT \
  --data-file data/btcirt_15m_2025-03-01_2026-03-01.csv \
  --capital 10000000 \
  --execution next_open \
  --seed 42
```

## Common mistakes to avoid

- using `context.data` instead of `context.history` for trading decisions
- returning raw strings instead of `Signal`
- producing indicator series with the wrong length
- producing indicator series with the wrong index
- assuming a strategy can open multiple simultaneous positions
- forgetting to clear cooldown, cache, or pending-order state in `reset()`
- adding exchange or portfolio logic inside the strategy

## Final instruction for AI agents

When asked to create a new strategy in this repository:

- write the new file in `strategies/user/`
- keep the code self-contained and readable
- follow the interface exactly
- optimize for correctness first, not complexity
