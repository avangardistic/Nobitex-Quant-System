"""Persistent session tracking for paper and live trading."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class SessionRecord:
    session_id: str
    mode: str
    strategy: str
    symbol: str
    status: str
    created_at: str
    updated_at: str
    capital: float
    config: dict[str, Any]
    pid: int | None = None
    report_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "mode": self.mode,
            "strategy": self.strategy,
            "symbol": self.symbol,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "capital": self.capital,
            "config": self.config,
            "pid": self.pid,
            "report_path": self.report_path,
        }


class SessionManager:
    """Read and write session state under the reports directory."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.root / "sessions.json"

    def _load_registry(self) -> dict[str, dict[str, Any]]:
        if not self.registry_path.exists():
            return {}
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def _save_registry(self, registry: dict[str, dict[str, Any]]) -> None:
        self.registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")

    def create(self, mode: str, strategy: str, symbol: str, capital: float, config: dict[str, Any]) -> SessionRecord:
        now = datetime.now(timezone.utc).isoformat()
        record = SessionRecord(
            session_id=uuid.uuid4().hex[:12],
            mode=mode,
            strategy=strategy,
            symbol=symbol,
            status="active",
            created_at=now,
            updated_at=now,
            capital=capital,
            config=config,
        )
        registry = self._load_registry()
        registry[record.session_id] = record.to_dict()
        self._save_registry(registry)
        return record

    def update(self, session_id: str, **changes: Any) -> SessionRecord:
        registry = self._load_registry()
        if session_id not in registry:
            raise KeyError(session_id)
        registry[session_id].update(changes)
        registry[session_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_registry(registry)
        return SessionRecord(**registry[session_id])

    def get(self, session_id: str) -> SessionRecord:
        registry = self._load_registry()
        if session_id not in registry:
            raise KeyError(session_id)
        return SessionRecord(**registry[session_id])

    def list(self, status: str | None = None) -> list[SessionRecord]:
        records = [SessionRecord(**payload) for payload in self._load_registry().values()]
        if status is None:
            return sorted(records, key=lambda item: item.created_at)
        return [record for record in records if record.status == status]

    def stop_flag(self, session_id: str) -> Path:
        return self.root / f"{session_id}.stop"

    def request_stop(self, session_id: str) -> Path:
        path = self.stop_flag(session_id)
        path.write_text("stop", encoding="utf-8")
        return path

    def clear_stop(self, session_id: str) -> None:
        path = self.stop_flag(session_id)
        if path.exists():
            path.unlink()
