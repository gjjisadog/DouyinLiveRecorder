from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.config import load_config
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
