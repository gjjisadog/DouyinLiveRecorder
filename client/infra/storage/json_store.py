"""Simple JSON storage helpers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import json
from pathlib import Path
from typing import Any

LoadErrorHandler = Callable[[Exception, Path, Path | None], None]


class JsonStore:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def load(self, default: Any = None, on_error: LoadErrorHandler | None = None) -> Any:
        if not self.file_path.exists():
            return default

        try:
            raw_text = self.file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            backup_path = self._quarantine_invalid_file()
            if on_error is not None:
                on_error(exc, self.file_path, backup_path)
            return default

        if not raw_text.strip():
            return default

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            backup_path = self._quarantine_invalid_file()
            if on_error is not None:
                on_error(exc, self.file_path, backup_path)
            return default

    def save(self, payload: Any) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _quarantine_invalid_file(self) -> Path | None:
        if not self.file_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        candidate = self.file_path.with_name(f"{self.file_path.stem}.broken-{timestamp}{self.file_path.suffix}")
        counter = 1
        while candidate.exists():
            candidate = self.file_path.with_name(
                f"{self.file_path.stem}.broken-{timestamp}-{counter}{self.file_path.suffix}"
            )
            counter += 1
        try:
            return self.file_path.replace(candidate)
        except OSError:
            return None
