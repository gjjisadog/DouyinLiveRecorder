"""Optional file-based automation bridge for packaged desktop client."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha1
from pathlib import Path
from typing import Any, Protocol

from PySide6.QtCore import QObject, QTimer

from client.infra.logging.log_service import LEVEL_ERROR, LEVEL_INFO, LEVEL_WARNING, LogEmitterMixin, LogHandler

AUTOMATION_DIR_ENV = "DLR_AUTOMATION_DIR"


def write_json_atomically(path: Path, payload: dict[str, Any]) -> None:
    temp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


class AutomationCommandHandler(Protocol):
    def handle_automation_command(self, command: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        ...


@dataclass(slots=True)
class AutomationPaths:
    root_dir: Path
    request_path: Path
    response_path: Path


class AutomationBridge(LogEmitterMixin):
    """Polls file-based automation requests and writes JSON responses."""

    def __init__(
        self,
        command_dir: Path,
        *,
        handler: AutomationCommandHandler,
        log_handler: LogHandler | None = None,
        poll_interval_ms: int = 250,
    ) -> None:
        super().__init__(log_handler=log_handler, log_source="automation")
        self.paths = AutomationPaths(
            root_dir=command_dir,
            request_path=command_dir / "request.json",
            response_path=command_dir / "response.json",
        )
        self.handler = handler
        self.poll_interval_ms = poll_interval_ms
        self._last_request_signature = ""
        self._timer: QTimer | None = None
        self.paths.root_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(
        cls,
        *,
        handler: AutomationCommandHandler,
        log_handler: LogHandler | None = None,
        poll_interval_ms: int = 250,
    ) -> "AutomationBridge | None":
        raw_path = os.environ.get(AUTOMATION_DIR_ENV, "").strip()
        if not raw_path:
            return None
        return cls(
            Path(raw_path),
            handler=handler,
            log_handler=log_handler,
            poll_interval_ms=poll_interval_ms,
        )

    def start(self, parent: QObject | None = None) -> None:
        if self._timer is not None:
            return
        self._timer = QTimer(parent)
        self._timer.setInterval(self.poll_interval_ms)
        self._timer.timeout.connect(self.poll_once)
        self._timer.start()
        self._emit_log(f"已启用自动化桥接：{self.paths.root_dir}", LEVEL_INFO)

    def stop(self) -> None:
        if self._timer is None:
            return
        self._timer.stop()
        self._timer.deleteLater()
        self._timer = None

    def poll_once(self) -> bool:
        if not self.paths.request_path.exists():
            return False

        raw_request = self.paths.request_path.read_text(encoding="utf-8")
        signature = sha1(raw_request.encode("utf-8")).hexdigest()
        if signature == self._last_request_signature:
            return False

        response: dict[str, Any]
        try:
            payload = json.loads(raw_request)
            if not isinstance(payload, dict):
                raise ValueError("automation request must be a JSON object")
            command = str(payload.get("command") or "").strip()
            if not command:
                raise ValueError("automation request missing command")
            request_id = str(payload.get("id") or signature)
            request_payload = payload.get("payload")
            if request_payload is None:
                request_payload = {}
            if not isinstance(request_payload, dict):
                raise ValueError("automation payload must be a JSON object")
            result = self.handler.handle_automation_command(command, request_payload)
            response = {
                "ok": True,
                "request_id": request_id,
                "command": command,
                "data": result,
                "processed_at": datetime.now().isoformat(timespec="seconds"),
            }
            self._emit_log(f"自动化命令已处理：{command}", LEVEL_INFO)
        except Exception as exc:
            response = {
                "ok": False,
                "request_id": None,
                "command": None,
                "error": str(exc),
                "processed_at": datetime.now().isoformat(timespec="seconds"),
            }
            self._emit_log(f"自动化命令处理失败：{exc}", LEVEL_ERROR)

        write_json_atomically(self.paths.response_path, response)
        self._last_request_signature = signature
        return True
