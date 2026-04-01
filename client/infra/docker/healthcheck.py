"""Healthcheck helpers for Docker/NAS deployments."""

from __future__ import annotations

import os
import sys
from pathlib import Path

DEFAULT_APP_ROOT = Path("/app")
DEFAULT_PROC_ROOT = Path("/proc")
DEFAULT_TARGET = "main.py"


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


def is_recorder_process_running(proc_root: Path, target_script: str = DEFAULT_TARGET) -> bool:
    target = target_script.lower()
    for cmdline in iter_process_cmdlines(proc_root):
        normalized = cmdline.lower()
        if target in normalized and "python" in normalized:
            return True
    return False


def run_healthcheck(
    app_root: Path = DEFAULT_APP_ROOT,
    proc_root: Path = DEFAULT_PROC_ROOT,
    target_script: str = DEFAULT_TARGET,
) -> tuple[bool, str]:
    config_path = url_config_path(app_root)
    entries = read_url_entries(config_path)
    if not entries:
        return False, f"URL config missing or empty: {config_path}"
    if not is_recorder_process_running(proc_root, target_script=target_script):
        return False, f"recorder process not running: {target_script}"
    return True, f"recorder healthy with {len(entries)} configured target(s)"


def main() -> int:
    app_root = Path(os.environ.get("DLR_HEALTHCHECK_ROOT", DEFAULT_APP_ROOT))
    proc_root = Path(os.environ.get("DLR_HEALTHCHECK_PROC_ROOT", DEFAULT_PROC_ROOT))
    target_script = os.environ.get("DLR_HEALTHCHECK_TARGET", DEFAULT_TARGET)
    healthy, message = run_healthcheck(app_root=app_root, proc_root=proc_root, target_script=target_script)
    print(message)
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
