from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from client.infra.docker.healthcheck import run_healthcheck


def test_healthcheck_uses_web_and_shared_daemon_state_without_process_scan() -> None:
    config = Path("/app/config/douyin.yaml")
    web = Mock(return_value=(True, "web healthy"))
    daemon = Mock(return_value=(True, "healthy"))

    healthy, message = run_healthcheck(
        daemon_config_path=config,
        web_url="http://127.0.0.1:18091/health",
        web_checker=web,
        daemon_checker=daemon,
    )

    assert healthy
    assert "share a healthy HealthState" in message
    web.assert_called_once()
    daemon.assert_called_once_with(config)


def test_healthcheck_propagates_daemon_failure() -> None:
    healthy, message = run_healthcheck(
        daemon_config_path=Path("/app/config/douyin.yaml"),
        web_checker=lambda _url: (True, "web healthy"),
        daemon_checker=lambda _path: (False, "heartbeat timeout"),
    )
    assert not healthy
    assert "heartbeat timeout" in message
