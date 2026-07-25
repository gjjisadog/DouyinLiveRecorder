from __future__ import annotations

from pathlib import Path
import threading
import time
from unittest.mock import AsyncMock, patch

import pytest

from app.config import load_config
from app.config_store import YamlConfigStore
from app.douyin_daemon import (
    DouyinDaemon,
    classify_recording_end,
    retry_delay,
    select_stream_url,
)


def test_stream_protocol_auto_prefers_hls_for_h265() -> None:
    result = {
        "flv_url": "https://example/live.flv?codec=h265",
        "m3u8_url": "https://example/live.m3u8?codec=h265",
    }
    assert select_stream_url(result, "auto").endswith("m3u8?codec=h265")


def test_stream_protocol_auto_prefers_flv_for_h264() -> None:
    result = {
        "flv_url": "https://example/live.flv?codec=h264",
        "m3u8_url": "https://example/live.m3u8?codec=h264",
    }
    assert select_stream_url(result, "auto").endswith("flv?codec=h264")


def test_retry_delay_is_exponential_and_capped() -> None:
    with patch("app.douyin_daemon.random.uniform", return_value=0):
        assert retry_delay(0) == 5
        assert retry_delay(3) == 40
        assert retry_delay(20) == 300


@pytest.mark.parametrize(
    ("code", "error", "stopping", "disk", "expected"),
    [
        (255, "", True, True, "user_stop"),
        (1, "No space left on device", False, False, "disk_space_low"),
        (0, "", False, True, "stream_ended"),
        (1, "HTTP error 403 Forbidden", False, True, "cookie_invalid"),
        (1, "captcha verify required", False, True, "risk_control"),
        (1, "Connection reset by peer", False, True, "network_disconnect"),
        (1, "Invalid data found", False, True, "ffmpeg_crash"),
    ],
)
def test_recording_end_classification(
    code: int, error: str, stopping: bool, disk: bool, expected: str
) -> None:
    assert (
        classify_recording_end(code, error, stopping=stopping, disk_available=disk)
        == expected
    )


def test_mocked_douyin_live_and_offline_responses(tmp_path: Path) -> None:
    config_file = tmp_path / "douyin.yaml"
    config_file.write_text(
        f"""
rooms:
  - url: https://live.douyin.com/123
storage:
  path: {tmp_path.as_posix()}/downloads
  state_path: {tmp_path.as_posix()}/state
  min_free_gb: 0.1
""",
        encoding="utf-8",
    )
    daemon = DouyinDaemon(load_config(config_file))
    live_data = {"id_str": "999", "anchor_name": "anchor", "status": 2}
    resolved = {"is_live": True, "flv_url": "https://example/live.flv"}
    with (
        patch(
            "app.douyin_daemon.spider.get_douyin_web_stream_data",
            new=AsyncMock(return_value=live_data),
        ),
        patch(
            "app.douyin_daemon.stream.get_douyin_stream_url",
            new=AsyncMock(return_value=resolved),
        ),
    ):
        _, result = daemon._resolve(daemon.config.rooms[0])
    assert result["is_live"] is True
    assert result["room_id"] == "999"
    daemon.pool.shutdown(wait=True)
    daemon.postprocess.shutdown(wait=True)


def test_daemon_hot_reload_atomically_switches_snapshot(tmp_path: Path) -> None:
    config_file = tmp_path / "douyin.yaml"
    config_file.write_text(
        f"""rooms:
  - url: https://live.douyin.com/123
    quality: original
    enabled: true
recorder:
  poll_seconds: 10
storage:
  path: {tmp_path.as_posix()}/downloads
  state_path: {tmp_path.as_posix()}/state
  min_free_gb: 0.1
""",
        encoding="utf-8",
    )
    daemon = DouyinDaemon(
        load_config(config_file, require_enabled_rooms=False),
        config_path=config_file,
    )
    store = YamlConfigStore(config_file)
    store.update(
        0,
        url="https://live.douyin.com/123",
        quality="hd",
        name="changed",
        enabled=True,
    )

    assert daemon.reload_config()
    assert daemon.config.rooms[0].quality == "hd"
    assert daemon.config.rooms[0].name == "changed"
    assert daemon.health.snapshot()["config_reload_error"] == ""
    daemon.pool.shutdown(wait=True)
    daemon.postprocess.shutdown(wait=True)


def test_invalid_hot_reload_keeps_previous_snapshot(tmp_path: Path) -> None:
    config_file = tmp_path / "douyin.yaml"
    config_file.write_text(
        f"""rooms:
  - url: https://live.douyin.com/123
storage:
  path: {tmp_path.as_posix()}/downloads
  state_path: {tmp_path.as_posix()}/state
  min_free_gb: 0.1
""",
        encoding="utf-8",
    )
    daemon = DouyinDaemon(
        load_config(config_file),
        config_path=config_file,
    )
    previous = daemon.config
    config_file.write_text("rooms: [invalid\n", encoding="utf-8")

    assert not daemon.reload_config()
    assert daemon.config is previous
    assert daemon.health.snapshot()["last_error_category"] == "configuration_invalid"
    daemon.pool.shutdown(wait=True)
    daemon.postprocess.shutdown(wait=True)


def test_disabling_room_stops_its_active_recording(tmp_path: Path) -> None:
    config_file = tmp_path / "douyin.yaml"
    config_file.write_text(
        f"""rooms:
  - url: https://live.douyin.com/123
storage:
  path: {tmp_path.as_posix()}/downloads
  state_path: {tmp_path.as_posix()}/state
  min_free_gb: 0.1
""",
        encoding="utf-8",
    )
    daemon = DouyinDaemon(load_config(config_file), config_path=config_file)
    daemon.recording_room_urls["recording-key"] = "https://live.douyin.com/123"
    stopped = threading.Event()
    store = YamlConfigStore(config_file)
    store.toggle(0)

    with patch.object(daemon.processes, "stop", side_effect=lambda keys: stopped.set()) as stop:
        assert daemon.reload_config()
        assert stopped.wait(2)

    stop.assert_called_once_with(["recording-key"])
    assert daemon.config.rooms == ()
    daemon.pool.shutdown(wait=True)
    daemon.postprocess.shutdown(wait=True)
