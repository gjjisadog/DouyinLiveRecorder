"""Desktop runtime helpers for tray behavior, startup, and crash recovery."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from client.infra.logging.log_service import LEVEL_INFO, LEVEL_WARNING, LogEmitterMixin, LogHandler, SOURCE_SYSTEM
from client.infra.storage.json_store import JsonStore

WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


@dataclass(slots=True)
class DesktopRuntimeState:
    last_exit_clean: bool = True
    running_task_ids: list[str] = field(default_factory=list)
    scheduler_running: bool = True
    current_tab_index: int = 0
    hidden_to_tray: bool = False
    updated_at: str = ""


class NullStartupAdapter:
    def is_enabled(self, name: str) -> bool:
        _ = name
        return False

    def enable(self, name: str, command: str) -> None:
        _ = (name, command)

    def disable(self, name: str) -> None:
        _ = name


class WindowsStartupAdapter:
    def __init__(self) -> None:
        import winreg

        self._winreg = winreg

    def is_enabled(self, name: str) -> bool:
        try:
            with self._winreg.OpenKey(self._winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY) as key:
                value, _ = self._winreg.QueryValueEx(key, name)
        except FileNotFoundError:
            return False
        return bool(str(value).strip())

    def enable(self, name: str, command: str) -> None:
        with self._winreg.CreateKey(self._winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY) as key:
            self._winreg.SetValueEx(key, name, 0, self._winreg.REG_SZ, command)

    def disable(self, name: str) -> None:
        try:
            with self._winreg.OpenKey(
                self._winreg.HKEY_CURRENT_USER,
                WINDOWS_RUN_KEY,
                0,
                self._winreg.KEY_SET_VALUE,
            ) as key:
                self._winreg.DeleteValue(key, name)
        except FileNotFoundError:
            return


def default_startup_adapter():
    if os.name == "nt":
        return WindowsStartupAdapter()
    return NullStartupAdapter()


def build_startup_command() -> str:
    executable = Path(sys.executable).resolve()
    if getattr(sys, "frozen", False):
        return f'"{executable}"'
    script = Path(sys.argv[0]).resolve()
    return f'"{executable}" "{script}"'


class DesktopRuntimeService(LogEmitterMixin):
    def __init__(
        self,
        runtime_state_path: Path,
        startup_name: str,
        startup_command: str,
        startup_adapter=None,
        log_handler: LogHandler | None = None,
    ) -> None:
        super().__init__(log_handler=log_handler, log_source=SOURCE_SYSTEM)
        self.runtime_state_path = runtime_state_path
        self.store = JsonStore(runtime_state_path)
        self.startup_name = startup_name
        self.startup_command = startup_command
        self.startup_adapter = startup_adapter or default_startup_adapter()

    def load_state(self) -> DesktopRuntimeState:
        payload = self.store.load(default={}, on_error=self._handle_store_error)
        if not isinstance(payload, dict):
            return DesktopRuntimeState()
        return self._deserialize_state(payload)

    def mark_launch_started(self) -> DesktopRuntimeState:
        previous_state = self.load_state()
        launch_state = DesktopRuntimeState(
            last_exit_clean=False,
            running_task_ids=list(previous_state.running_task_ids),
            scheduler_running=previous_state.scheduler_running,
            current_tab_index=previous_state.current_tab_index,
            hidden_to_tray=previous_state.hidden_to_tray,
            updated_at=self._timestamp(),
        )
        self.save_state(launch_state)
        return previous_state

    def save_state(self, state: DesktopRuntimeState) -> None:
        payload = self._serialize_state(state)
        self.store.save(payload)

    def mark_clean_exit(self, state: DesktopRuntimeState | None = None) -> None:
        final_state = state or self.load_state()
        final_state.last_exit_clean = True
        final_state.updated_at = self._timestamp()
        self.save_state(final_state)

    def is_startup_enabled(self) -> bool:
        return bool(self.startup_adapter.is_enabled(self.startup_name))

    def apply_startup_setting(self, enabled: bool) -> bool:
        if enabled:
            self.startup_adapter.enable(self.startup_name, self.startup_command)
            self._emit_log("已启用开机启动。", LEVEL_INFO)
        else:
            self.startup_adapter.disable(self.startup_name)
            self._emit_log("已关闭开机启动。", LEVEL_INFO)
        return self.is_startup_enabled()

    def _serialize_state(self, state: DesktopRuntimeState) -> dict:
        return {
            "version": 1,
            "last_exit_clean": state.last_exit_clean,
            "running_task_ids": list(dict.fromkeys(state.running_task_ids)),
            "scheduler_running": state.scheduler_running,
            "current_tab_index": state.current_tab_index,
            "hidden_to_tray": state.hidden_to_tray,
            "updated_at": state.updated_at or self._timestamp(),
        }

    def _deserialize_state(self, payload: dict) -> DesktopRuntimeState:
        return DesktopRuntimeState(
            last_exit_clean=bool(payload.get("last_exit_clean", True)),
            running_task_ids=[str(item) for item in payload.get("running_task_ids", []) if str(item).strip()],
            scheduler_running=bool(payload.get("scheduler_running", True)),
            current_tab_index=max(0, int(payload.get("current_tab_index", 0))),
            hidden_to_tray=bool(payload.get("hidden_to_tray", False)),
            updated_at=str(payload.get("updated_at") or ""),
        )

    def _handle_store_error(self, exc: Exception, path: Path, backup_path: Path | None) -> None:
        suffix = f"，已备份到 {backup_path}" if backup_path is not None else ""
        self._emit_log(f"读取桌面运行状态失败：{path}。{exc}{suffix}", LEVEL_WARNING)

    def _timestamp(self) -> str:
        return datetime.now().isoformat(timespec="seconds")
