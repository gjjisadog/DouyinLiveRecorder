from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from .config import ConfigError, load_config


class HealthState:
    def __init__(self, state_path: Path) -> None:
        self.path = state_path / "health.json"
        self._thread_lock = threading.RLock()
        self._async_lock: asyncio.Lock | None = None
        self.state: dict[str, Any] = {
            "started_at": time.time(),
            "heartbeat_at": 0.0,
            "last_check_at": 0.0,
            "check_failures": 0,
            "ffmpeg_crashes": 0,
            "ffmpeg_crashes_window": 0,
            "ffmpeg_crashes_total": 0,
            "ffmpeg_consecutive_crashes": 0,
            "ffmpeg_crash_window_seconds": 1800.0,
            "last_successful_recording_at": 0.0,
            "last_ffmpeg_return_code": None,
            "last_ffmpeg_error": "",
            "last_error_category": "",
            "active_recordings": 0,
            "configured_rooms": 0,
            "disk_free_gb": 0.0,
            "config_reloaded_at": 0.0,
            "config_reload_error": "",
            "stopping": False,
        }

    def update(self, **values: Any) -> None:
        with self._thread_lock:
            self.state.update(values)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
            )
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as temporary:
                    json.dump(self.state, temporary, ensure_ascii=False)
                    temporary.flush()
                    os.fsync(temporary.fileno())
                os.replace(temporary_name, self.path)
            finally:
                try:
                    os.unlink(temporary_name)
                except FileNotFoundError:
                    pass

    async def update_async(self, **values: Any) -> None:
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        async with self._async_lock:
            await asyncio.to_thread(self.update, **values)

    def snapshot(self) -> dict[str, Any]:
        with self._thread_lock:
            return dict(self.state)


def read_health_state(state_path: Path) -> dict[str, Any]:
    health_file = state_path / "health.json"
    try:
        payload = json.loads(health_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"健康状态不可用: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("健康状态格式错误")
    return payload


def check(config_path: Path, state_path: Path | None = None) -> tuple[bool, str]:
    config = None
    if state_path is None:
        try:
            config = load_config(config_path, require_enabled_rooms=False)
        except ConfigError as exc:
            return False, str(exc)
        state_path = config.storage.state_path
    try:
        state = read_health_state(state_path)
    except ValueError as exc:
        return False, str(exc)
    now = time.time()
    poll_seconds = int(
        state.get("poll_seconds")
        or (config.recorder.poll_seconds if config is not None else 120)
    )
    max_age = max(poll_seconds * 3, 180)
    if state.get("stopping"):
        return False, "服务正在停止"
    if now - float(state.get("heartbeat_at", 0)) > max_age:
        return False, "主调度循环心跳超时"
    if now - float(state.get("last_check_at", 0)) > max_age * 2:
        return False, "抖音状态检测长时间未完成"
    crash_count = int(state.get("ffmpeg_crashes_window", state.get("ffmpeg_crashes", 0)))
    if crash_count >= 5:
        return False, "FFmpeg 持续崩溃"
    storage_path = Path(
        str(
            state.get("storage_path")
            or (config.storage.path if config is not None else "/data/downloads")
        )
    )
    min_free_gb = float(
        state.get("min_free_gb")
        or (config.storage.min_free_gb if config is not None else 10.0)
    )
    free_gb = shutil.disk_usage(storage_path).free / (1024**3)
    if free_gb < min_free_gb:
        return False, f"磁盘空间不足: {free_gb:.2f} GiB"
    return True, "healthy"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Douyin daemon health check")
    parser.add_argument("command", choices=["check"])
    parser.add_argument(
        "--config",
        default=os.environ.get("DOUYIN_CONFIG", "/app/config/douyin.yaml"),
    )
    args = parser.parse_args(argv)
    state_path_value = os.environ.get("DLR_STATE_PATH", "").strip()
    healthy, message = check(
        Path(args.config),
        Path(state_path_value) if state_path_value else None,
    )
    print(message)
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
