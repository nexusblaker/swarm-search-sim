"""Lightweight file-based event logging and replay helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


class EventLogger:
    """Collects structured events and writes replay artifacts."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record(self, event_type: str, step: int, **payload: Any) -> None:
        self.events.append(
            self._sanitize({"event_type": event_type, "step": step, **payload})
        )

    def save_jsonl(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            for event in self.events:
                handle.write(json.dumps(self._sanitize(event)) + "\n")
        return output_path

    @staticmethod
    def save_replay(history: list[dict[str, Any]], path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(EventLogger._sanitize(history), handle)
        return output_path

    @staticmethod
    def load_replay(path: str | Path) -> list[dict[str, Any]]:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _sanitize(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                EventLogger._sanitize_key(key): EventLogger._sanitize(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [EventLogger._sanitize(item) for item in value]
        if isinstance(value, set):
            return [EventLogger._sanitize(item) for item in sorted(value, key=str)]
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, Path):
            return str(value)
        return value

    @staticmethod
    def _sanitize_key(key: Any) -> str:
        if isinstance(key, str):
            return key
        if isinstance(key, tuple):
            return ",".join(str(part) for part in key)
        return str(key)
