from __future__ import annotations

import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import ConfigError
from app.config_store import YamlConfigStore
from app.health import HealthState
from client.infra.docker.config_web import create_server

TOKEN = "test-web-token-value-123456"


def write_config(path: Path, tmp_path: Path) -> None:
    path.write_text(
        f"""rooms:
  - url: https://live.douyin.com/123
    name: first
    quality: original
    enabled: true
recorder:
  format: ts
  poll_seconds: 10
  segment_seconds: 60
  max_concurrent_checks: 1
storage:
  path: {tmp_path.as_posix()}/downloads
  state_path: {tmp_path.as_posix()}/state
  min_free_gb: 0.1
cookie:
  value: ""
""",
        encoding="utf-8",
    )


def start_server(tmp_path: Path):
    config = tmp_path / "douyin.yaml"
    write_config(config, tmp_path)
    (tmp_path / "downloads").mkdir()
    state_path = tmp_path / "state"
    health = HealthState(state_path)
    health.update(
        heartbeat_at=10**10,
        last_check_at=10**10,
        configured_rooms=1,
        active_recordings=0,
        disk_free_gb=123.5,
        storage_path=str(tmp_path / "downloads"),
        min_free_gb=0.1,
        poll_seconds=10,
        last_error_category="",
        stopping=False,
    )
    server = create_server(
        config_path=config,
        log_dir=tmp_path / "logs",
        state_path=state_path,
        host="127.0.0.1",
        port=0,
        token=TOKEN,
    )
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    return server, thread, config


def authorized_request(url: str, *, data: bytes | None = None, cookie: str = ""):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    if cookie:
        headers["Cookie"] = cookie
    return urllib.request.Request(url, data=data, headers=headers)


def authenticated_page(server) -> tuple[str, str, str]:
    host, port = server.server_address
    response = urllib.request.urlopen(authorized_request(f"http://{host}:{port}/"), timeout=5)
    body = response.read().decode("utf-8")
    cookie = response.headers["Set-Cookie"].split(";", 1)[0]
    token = re.search(r'name="csrf_token" value="([^"]+)"', body)
    assert token
    return body, cookie, token.group(1)


def stop_server(server, thread: threading.Thread) -> None:
    server.stop_accepting_writes()
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)


def test_yaml_store_add_update_toggle_delete_and_atomic_validation(tmp_path: Path) -> None:
    config = tmp_path / "douyin.yaml"
    write_config(config, tmp_path)
    store = YamlConfigStore(config)

    store.add(url="https://live.douyin.com/456", name="second", quality="hd")
    store.update(
        1,
        url="https://www.douyin.com/user/MS4wLjAB",
        name="updated",
        quality="sd",
        enabled=True,
    )
    store.toggle(0)
    rooms = store.list_rooms()
    assert rooms[0].enabled is False
    assert rooms[1].name == "updated"
    assert rooms[1].quality == "sd"
    store.delete(0)
    assert len(store.list_rooms()) == 1
    assert not list(tmp_path.glob(".douyin.yaml.*.tmp"))


def test_invalid_web_mutation_keeps_previous_yaml(tmp_path: Path) -> None:
    config = tmp_path / "douyin.yaml"
    write_config(config, tmp_path)
    store = YamlConfigStore(config)
    before = config.read_bytes()

    with pytest.raises(ConfigError, match="支持的抖音地址"):
        store.add(url="https://example.com/not-douyin")

    assert config.read_bytes() == before


def test_validation_failure_does_not_replace_existing_yaml(tmp_path: Path) -> None:
    config = tmp_path / "douyin.yaml"
    write_config(config, tmp_path)
    store = YamlConfigStore(config)
    before = config.read_bytes()

    with (
        patch("app.config_store.load_config", side_effect=ConfigError("invalid candidate")),
        pytest.raises(ConfigError, match="invalid candidate"),
    ):
        store.toggle(0)

    assert config.read_bytes() == before
    assert not list(tmp_path.glob(".douyin.yaml.*.tmp"))


def test_web_refuses_to_rewrite_plaintext_cookie(tmp_path: Path) -> None:
    config = tmp_path / "douyin.yaml"
    write_config(config, tmp_path)
    content = config.read_text(encoding="utf-8").replace('value: ""', "value: ttwid=secret")
    config.write_text(content, encoding="utf-8")
    store = YamlConfigStore(config)
    before = config.read_bytes()

    with pytest.raises(ConfigError, match="DOUYIN_COOKIE_FILE"):
        store.toggle(0)

    assert config.read_bytes() == before


def test_management_pages_require_token_and_writes_require_csrf(tmp_path: Path) -> None:
    server, thread, _ = start_server(tmp_path)
    try:
        host, port = server.server_address
        url = f"http://{host}:{port}/"
        with pytest.raises(urllib.error.HTTPError) as unauthorized:
            urllib.request.urlopen(url, timeout=5)
        assert unauthorized.value.code == 401

        body, cookie, csrf = authenticated_page(server)
        assert "daemon 真实状态" in body
        assert "123.50 GiB" in body

        no_csrf = authorized_request(
            f"http://{host}:{port}/rooms/add",
            data=urllib.parse.urlencode(
                {"url": "https://live.douyin.com/456", "quality": "hd"}
            ).encode(),
        )
        with pytest.raises(urllib.error.HTTPError) as forbidden:
            urllib.request.urlopen(no_csrf, timeout=5)
        assert forbidden.value.code == 403

        payload = urllib.parse.urlencode(
            {
                "csrf_token": csrf,
                "url": "https://live.douyin.com/456",
                "name": "new",
                "quality": "hd",
                "enabled": "1",
            }
        ).encode()
        response = urllib.request.urlopen(
            authorized_request(
                f"http://{host}:{port}/rooms/add",
                data=payload,
                cookie=cookie,
            ),
            timeout=5,
        )
        assert response.status == 200
        assert len(server.store.list_rooms()) == 2
    finally:
        stop_server(server, thread)


def test_public_bind_requires_token(tmp_path: Path) -> None:
    config = tmp_path / "douyin.yaml"
    write_config(config, tmp_path)
    with pytest.raises(RuntimeError, match="未鉴权"):
        create_server(config_path=config, host="0.0.0.0", port=0, token="")


def test_request_body_size_is_limited(tmp_path: Path) -> None:
    server, thread, _ = start_server(tmp_path)
    try:
        host, port = server.server_address
        request = authorized_request(
            f"http://{host}:{port}/rooms/add",
            data=b"x" * (64 * 1024 + 1),
        )
        with pytest.raises(urllib.error.HTTPError) as too_large:
            urllib.request.urlopen(request, timeout=5)
        assert too_large.value.code == 413
    finally:
        stop_server(server, thread)
