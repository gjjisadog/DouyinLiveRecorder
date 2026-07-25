"""Healthcheck for the NAS Web and its shared daemon HealthState."""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

from app.health import check as check_daemon_health

DEFAULT_APP_ROOT = Path("/app")
DEFAULT_WEB_URL = "http://127.0.0.1:18091/health"


def check_web_health(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return False, f"web health returned HTTP {response.status}"
    except (OSError, urllib.error.URLError) as exc:
        return False, f"web health unavailable: {exc}"
    return True, "web healthy"


def run_healthcheck(
    *,
    daemon_config_path: Path,
    state_path: Path | None = None,
    web_url: str = DEFAULT_WEB_URL,
    web_checker: Callable[[str], tuple[bool, str]] = check_web_health,
    daemon_checker: Callable[[Path], tuple[bool, str]] = check_daemon_health,
) -> tuple[bool, str]:
    web_healthy, web_message = web_checker(web_url)
    if not web_healthy:
        return False, web_message
    if state_path is None:
        daemon_healthy, daemon_message = daemon_checker(daemon_config_path)
    else:
        daemon_healthy, daemon_message = check_daemon_health(
            daemon_config_path,
            state_path,
        )
    if not daemon_healthy:
        return False, f"daemon unhealthy: {daemon_message}"
    return True, "web and daemon share a healthy HealthState"


def main() -> int:
    app_root = Path(os.environ.get("DLR_HEALTHCHECK_ROOT", DEFAULT_APP_ROOT))
    config_path = Path(
        os.environ.get("DOUYIN_CONFIG", str(app_root / "config" / "douyin.yaml"))
    )
    web_url = os.environ.get("DLR_HEALTHCHECK_WEB_URL", DEFAULT_WEB_URL)
    state_path = Path(os.environ.get("DLR_STATE_PATH", "/data/state"))
    healthy, message = run_healthcheck(
        daemon_config_path=config_path,
        state_path=state_path,
        web_url=web_url,
    )
    print(message)
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
