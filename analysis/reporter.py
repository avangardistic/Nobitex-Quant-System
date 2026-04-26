"""Report generation for JSON, CSV, and HTML outputs.

Limitations:
- HTML reports are intentionally simple and self-contained.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def write_json_report(path: str | Path, payload: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def write_csv_report(path: str | Path, trades: list[dict]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(trades).to_csv(path, index=False)
    return path


def write_html_report(path: str | Path, payload: dict) -> Path:
    trust = payload.get("trust", {})
    html = f"""
    <html>
      <head><title>Backtest Report</title></head>
      <body>
        <h1>Backtest Report</h1>
        <h2>Metrics</h2>
        <pre>{json.dumps(payload.get('metrics', {}), indent=2)}</pre>
        <h2>Trust & Correctness</h2>
        <pre>{json.dumps(trust, indent=2)}</pre>
      </body>
    </html>
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html.strip(), encoding="utf-8")
    return path
