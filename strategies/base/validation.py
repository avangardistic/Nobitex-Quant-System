"""Strategy loading and validation helpers.

Limitations:
- Validation checks interface contracts and anti-lookahead heuristics, not economic edge.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pandas as pd

from core.exceptions import ValidationError
from strategies.base.context import StrategyContext
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy


SAMPLE_COLUMNS = ["open", "high", "low", "close", "volume"]


def load_module(path: str | Path) -> ModuleType:
    path = Path(path)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ValidationError(f"Cannot load strategy module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discover_strategy_class(module: ModuleType) -> type[BaseStrategy]:
    for value in module.__dict__.values():
        if isinstance(value, type) and issubclass(value, BaseStrategy) and value is not BaseStrategy:
            return value
    raise ValidationError("No BaseStrategy subclass found")


def sample_data(length: int = 80) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=length, freq="h", tz="UTC")
    prices = pd.Series(range(100, 100 + length), index=index, dtype=float)
    frame = pd.DataFrame(
        {
            "open": prices,
            "high": prices + 1,
            "low": prices - 1,
            "close": prices + 0.5,
            "volume": 1000.0,
        },
        index=index,
    )
    return frame[SAMPLE_COLUMNS]


def _strategy_factory(strategy: BaseStrategy) -> type[BaseStrategy]:
    strategy_cls = strategy.__class__
    try:
        strategy_cls()
    except TypeError as exc:
        raise ValidationError(f"{strategy_cls.__name__} must be instantiable without constructor arguments") from exc
    return strategy_cls


def _replay_signals(strategy: BaseStrategy, data: pd.DataFrame) -> list[str | None]:
    strategy.reset()
    outputs: list[str | None] = []
    for current_index in range(1, len(data)):
        context = StrategyContext(symbol="BTCIRT", data=data, history=data.iloc[:current_index], current_index=current_index)
        signal = strategy.generate_signal(context)
        if signal is not None and not isinstance(signal, Signal):
            raise ValidationError("generate_signal must return Signal or None")
        outputs.append(None if signal is None else repr(signal))
    return outputs


def _lookahead_safe_over_replay(strategy_cls: type[BaseStrategy], data: pd.DataFrame) -> bool:
    close_idx = data.columns.get_loc("close")
    for current_index in range(1, len(data)):
        baseline = strategy_cls()
        shifted = strategy_cls()
        baseline_signal = _replay_signals(baseline, data.iloc[: current_index + 1])[-1]
        shifted_data = data.copy()
        shifted_data.iloc[current_index:, close_idx] += 1000
        shifted_signal = _replay_signals(shifted, shifted_data.iloc[: current_index + 1])[-1]
        if baseline_signal != shifted_signal:
            return False
    return True


def validate_strategy_instance(strategy: BaseStrategy, data: pd.DataFrame | None = None) -> dict[str, object]:
    data = data.copy() if data is not None else sample_data()
    strategy_cls = _strategy_factory(strategy)
    indicators = strategy.calculate_indicators(data)
    if not isinstance(indicators, dict):
        raise ValidationError("calculate_indicators must return a dict")
    for name, series in indicators.items():
        if not isinstance(series, pd.Series):
            raise ValidationError(f"Indicator {name} must be a pandas Series")
        if len(series) != len(data):
            raise ValidationError(f"Indicator {name} length mismatch")
        if not series.index.equals(data.index):
            raise ValidationError(f"Indicator {name} index must align with input data")
    strategy.reset()
    context = StrategyContext(symbol="BTCIRT", data=data, history=data.iloc[:-1], current_index=len(data) - 1)
    signal = strategy.generate_signal(context)
    if signal is not None and not isinstance(signal, Signal):
        raise ValidationError("generate_signal must return Signal or None")
    shifted = data.copy()
    shifted.iloc[-1, shifted.columns.get_loc("close")] += 1000
    strategy.reset()
    context_shifted = StrategyContext(symbol="BTCIRT", data=shifted, history=shifted.iloc[:-1], current_index=len(shifted) - 1)
    shifted_signal = strategy.generate_signal(context_shifted)
    lookahead_safe = repr(signal) == repr(shifted_signal) and _lookahead_safe_over_replay(strategy_cls, data)
    first_replay = _replay_signals(strategy, data)
    second_replay = _replay_signals(strategy, data)
    replay_matches_after_reset = first_replay == second_replay
    fresh_instance_replay = _replay_signals(strategy_cls(), data)
    deterministic_across_instances = first_replay == fresh_instance_replay
    if not lookahead_safe:
        raise ValidationError("Strategy failed lookahead validation")
    if not replay_matches_after_reset:
        raise ValidationError("Strategy state is not reset cleanly between runs")
    if not deterministic_across_instances:
        raise ValidationError("Strategy outputs differ across identical fresh instances")
    return {
        "indicators": list(indicators.keys()),
        "signal_type": None if signal is None else signal.action,
        "lookahead_safe": lookahead_safe,
        "replay_matches_after_reset": replay_matches_after_reset,
        "deterministic_across_instances": deterministic_across_instances,
    }


def validate_strategy_file(path: str | Path) -> dict[str, object]:
    module = load_module(path)
    strategy_cls = discover_strategy_class(module)
    strategy = strategy_cls()
    result = validate_strategy_instance(strategy)
    result["strategy_class"] = strategy_cls.__name__
    result["path"] = str(path)
    return result
