"""Execution profile models for static and calibrated backtest cost modes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExecutionProfile:
    symbol: str
    mode: str = "static"
    commission_rate: float = 0.0015
    spread_bps: float = 5.0
    slippage_bps: float = 5.0
    calibrated_at: str | None = None
    sample_count: int = 0
    depth_levels: list[dict[str, float]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def profile_hash(self) -> str:
        material = json.dumps(self.to_dict(), sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str | Path) -> "ExecutionProfile":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**payload)
