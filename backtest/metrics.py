"""Portfolio metrics for backtest reports.

Limitations:
- Assumes evenly spaced observations for annualization.
"""

from __future__ import annotations

import math

import pandas as pd


def total_return(equity_curve: pd.Series) -> float:
    if equity_curve.empty:
        return 0.0
    return float(equity_curve.iloc[-1] / equity_curve.iloc[0] - 1)


def sharpe_ratio(returns: pd.Series, periods_per_year: int = 365) -> float:
    returns = returns.dropna()
    if returns.empty or returns.std() == 0:
        return 0.0
    return float((returns.mean() / returns.std()) * math.sqrt(periods_per_year))


def sortino_ratio(returns: pd.Series, periods_per_year: int = 365) -> float:
    downside = returns[returns < 0]
    if returns.dropna().empty or downside.std() == 0 or pd.isna(downside.std()):
        return 0.0
    return float((returns.mean() / downside.std()) * math.sqrt(periods_per_year))


def max_drawdown(equity_curve: pd.Series) -> float:
    if equity_curve.empty:
        return 0.0
    running_max = equity_curve.cummax()
    drawdown = (equity_curve / running_max) - 1
    return abs(float(drawdown.min()))


def summarize(equity_curve: pd.Series) -> dict[str, float]:
    returns = equity_curve.pct_change().fillna(0)
    return {
        "total_return": total_return(equity_curve),
        "sharpe": sharpe_ratio(returns),
        "sortino": sortino_ratio(returns),
        "max_drawdown": max_drawdown(equity_curve),
    }
