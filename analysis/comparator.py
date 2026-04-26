"""Compare two backtest runs for reproducibility.

Limitations:
- Comparison focuses on top-level metrics, trust hash, and trade counts.
"""

from __future__ import annotations


def compare_runs(first: dict, second: dict) -> dict[str, object]:
    return {
        "metrics_equal": first.get("metrics") == second.get("metrics"),
        "trade_count_equal": len(first.get("trades", [])) == len(second.get("trades", [])),
        "trust_hash_equal": first.get("trust", {}).get("reproducibility_hash") == second.get("trust", {}).get("reproducibility_hash"),
    }
