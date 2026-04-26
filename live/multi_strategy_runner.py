"""Run multiple strategies independently on the same market data.

Limitations:
- Strategies are sequenced in-process and share no capital allocator.
"""

from __future__ import annotations


def run_strategies(strategies: list, symbol: str, frame) -> dict[str, list]:
    results: dict[str, list] = {}
    for strategy in strategies:
        signals = []
        for current_index in range(1, len(frame)):
            context = __import__("strategies.base.context", fromlist=["StrategyContext"]).StrategyContext(
                symbol=symbol,
                data=frame,
                history=frame.iloc[:current_index],
                current_index=current_index,
            )
            signal = strategy.generate_signal(context)
            if signal is not None:
                signals.append(signal.action)
        results[strategy.name] = signals
    return results
