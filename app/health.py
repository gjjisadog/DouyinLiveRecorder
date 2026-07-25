from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from .config import ConfigError, load_config


class HealthState:
    def __init__(self, state_path: Path) -> None:
        self.path = state_path / "health.json"
        self.state: dict[str, Any] = {
            "started_at": time.time(),
            "heartbeat_at": 0.0,
            "last_check_at": 0.0,
            "check_failures": 0,
            "ffmpeg_crashes": 0,
            "last_ffmpeg_return_code": None,
            "last_ffmpeg_error": "",
            "active_recordings": 0,
            "stopping": False,
        }

    def update(self, **values: Any) -> None:
        self.state.update(values)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, self.path)


def check(config_path: Path) -> tuple[bool, str]:
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        return False, str(exc)
    health_file = config.storage.state_path / "health.json"
    try:
        state = json.loads(health_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return False, f"健康状态不可用: {exc}"
    now = time.time()
    max_age = max(config.recorder.poll_seconds * 3, 180)
    if state.get("stopping"):
        return False, "服务正在停止"
    if now - float(state.get("heartbeat_at", 0)) > max_age:
        return False, "主调度循环心跳超时"
    if now - float(state.get("last_check_at", 0)) > max_age * 2:
        return False, "抖音状态检测长时间未完成"
    if int(state.get("ffmpeg_crashes", 0)) >= 5:
        return False, "FFmpeg 持续崩溃"
    free_gb = shutil.disk_usage(config.storage.path).free / (1024**3)
    if free_gb < config.storage.min_free_gb:
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
    healthy, message = check(Path(args.config))
    print(message)
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
