"""Healthcheck helpers for Docker/NAS deployments."""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

from app.health import check as check_daemon_health

DEFAULT_APP_ROOT = Path("/app")
DEFAULT_PROC_ROOT = Path("/proc")
DEFAULT_TARGET = "app.douyin_daemon"
DEFAULT_LEGACY_TARGET = "main.py"
DEFAULT_LAUNCHER_TARGET = "client.infra.docker.launcher"
DEFAULT_WEB_URL = "http://127.0.0.1:18091/health"


def url_config_path(app_root: Path) -> Path:
    return app_root / "config" / "URL_config.ini"


def read_url_entries(path: Path) -> list[str]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8-sig", errors="ignore")
    entries: list[str] = []
    for line in content.splitlines():
        normalized = line.strip()
        if not normalized or normalized.startswith("#"):
            continue
        entries.append(normalized)
    return entries


def iter_process_cmdlines(proc_root: Path) -> list[str]:
    cmdlines: list[str] = []
    if not proc_root.exists():
        return cmdlines
    for proc_dir in proc_root.iterdir():
        if not proc_dir.is_dir() or not proc_dir.name.isdigit():
            continue
        cmdline_path = proc_dir / "cmdline"
        try:
            raw_cmdline = cmdline_path.read_bytes()
        except OSError:
            continue
        if not raw_cmdline:
            continue
        cmdlines.append(raw_cmdline.replace(b"\x00", b" ").decode("utf-8", errors="ignore").strip())
    return cmdlines


def is_python_process_running(proc_root: Path, target: str) -> bool:
    normalized_target = target.lower()
    for cmdline in iter_process_cmdlines(proc_root):
        normalized = cmdline.lower()
        if normalized_target in normalized and "python" in normalized:
            return True
    return False


def is_recorder_process_running(proc_root: Path, target_script: str = DEFAULT_TARGET) -> bool:
    return is_python_process_running(proc_root, target_script)


def is_launcher_process_running(proc_root: Path, target_script: str = DEFAULT_LAUNCHER_TARGET) -> bool:
    return is_python_process_running(proc_root, target_script)


def check_web_health(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return False, f"web health returned HTTP {response.status}"
    except (OSError, urllib.error.URLError) as exc:
        return False, f"web health unavailable: {exc}"
    return True, "web healthy"


def run_healthcheck(
    app_root: Path = DEFAULT_APP_ROOT,
    proc_root: Path = DEFAULT_PROC_ROOT,
    target_script: str = DEFAULT_TARGET,
    launcher_target: str = DEFAULT_LAUNCHER_TARGET,
    recorder_mode: str = "daemon",
    daemon_config_path: Path | None = None,
    web_url: str | None = None,
    web_checker: Callable[[str], tuple[bool, str]] = check_web_health,
    daemon_checker: Callable[[Path], tuple[bool, str]] = check_daemon_health,
) -> tuple[bool, str]:
    if not is_launcher_process_running(proc_root, target_script=launcher_target):
        return False, f"launcher process not running: {launcher_target}"
    if web_url:
        web_healthy, web_message = web_checker(web_url)
        if not web_healthy:
            return False, web_message
    if recorder_mode == "daemon":
        resolved_config_path = daemon_config_path or app_root / "config" / "douyin.yaml"
        if not is_recorder_process_running(proc_root, target_script=target_script):
            return False, f"recorder process not running: {target_script}"
        daemon_healthy, daemon_message = daemon_checker(resolved_config_path)
        if not daemon_healthy:
            return False, f"daemon unhealthy: {daemon_message}"
        return True, "launcher, web and daemon healthy"
    if recorder_mode != "legacy":
        return False, f"unsupported recorder mode: {recorder_mode}"
    config_path = url_config_path(app_root)
    entries = read_url_entries(config_path)
    if not entries:
        return True, f"waiting for configuration: {config_path}"
    if not is_recorder_process_running(proc_root, target_script=DEFAULT_LEGACY_TARGET):
        return False, f"recorder process not running: {DEFAULT_LEGACY_TARGET}"
    return True, f"recorder healthy with {len(entries)} configured target(s)"


def main() -> int:
    app_root = Path(os.environ.get("DLR_HEALTHCHECK_ROOT", DEFAULT_APP_ROOT))
    proc_root = Path(os.environ.get("DLR_HEALTHCHECK_PROC_ROOT", DEFAULT_PROC_ROOT))
    target_script = os.environ.get("DLR_HEALTHCHECK_TARGET", DEFAULT_TARGET)
    launcher_target = os.environ.get("DLR_HEALTHCHECK_LAUNCHER_TARGET", DEFAULT_LAUNCHER_TARGET)
    recorder_mode = os.environ.get("DLR_RECORDER_MODE", "daemon").strip().lower()
    daemon_config_path = Path(
        os.environ.get("DOUYIN_CONFIG", str(app_root / "config" / "douyin.yaml"))
    )
    web_url = os.environ.get("DLR_HEALTHCHECK_WEB_URL", DEFAULT_WEB_URL)
    healthy, message = run_healthcheck(
        app_root=app_root,
        proc_root=proc_root,
        target_script=target_script,
        launcher_target=launcher_target,
        recorder_mode=recorder_mode,
        daemon_config_path=daemon_config_path,
        web_url=web_url,
    )
    print(message)
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
