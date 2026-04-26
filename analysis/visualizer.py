"""Data structures used by charting layers.

Limitations:
- Returns serializable chart payloads instead of rendering interactive plots directly.
"""

from __future__ import annotations

import pandas as pd


def equity_chart_payload(equity_curve: pd.Series) -> dict[str, list]:
    return {"x": [str(index) for index in equity_curve.index], "y": [float(value) for value in equity_curve.values]}
