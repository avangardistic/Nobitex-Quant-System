"""Additional statistics helpers.

Limitations:
- Assumes the trade list already contains realized PnL.
"""

from __future__ import annotations


def trade_stats(trades: list[dict]) -> dict[str, float]:
    if not trades:
        return {"win_rate": 0.0, "avg_pnl": 0.0}
    wins = sum(1 for trade in trades if trade["pnl"] > 0)
    avg_pnl = sum(trade["pnl"] for trade in trades) / len(trades)
    return {"win_rate": wins / len(trades), "avg_pnl": avg_pnl}
