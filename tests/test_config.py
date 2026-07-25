from __future__ import annotations

from pathlib import Path

import pytest

from app.config import ConfigError, load_config, load_cookie, normalize_douyin_url, redact_secret


def write_config(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_normalize_douyin_room_user_and_short_urls() -> None:
    assert normalize_douyin_url("https://live.douyin.com/123?foo=1") == (
        "https://live.douyin.com/123",
        "room:123",
    )
    assert normalize_douyin_url("https://www.douyin.com/user/MS4wLjAB") == (
        "https://www.douyin.com/user/MS4wLjAB",
        "user:MS4wLjAB",
    )
    assert normalize_douyin_url("https://v.douyin.com/AbCd/") == (
        "https://v.douyin.com/AbCd/",
        "short:abcd",
    )


def test_config_deduplicates_normalized_rooms(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path / "douyin.yaml",
        f"""
rooms:
  - url: https://live.douyin.com/123?from=a
  - url: https://live.douyin.com/123
storage:
  path: {tmp_path.as_posix()}/downloads
  state_path: {tmp_path.as_posix()}/state
  min_free_gb: 0.1
""",
    )
    config = load_config(config_path)
    assert len(config.rooms) == 1
    assert config.rooms[0].url == "https://live.douyin.com/123"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("poll_seconds", 9, "recorder.poll_seconds"),
        ("segment_seconds", 59, "recorder.segment_seconds"),
        ("max_concurrent_checks", 0, "recorder.max_concurrent_checks"),
    ],
)
def test_config_reports_specific_range_errors(
    tmp_path: Path, field: str, value: int, message: str
) -> None:
    config_path = write_config(
        tmp_path / "bad.yaml",
        f"""
rooms:
  - url: https://live.douyin.com/123
recorder:
  {field}: {value}
storage:
  path: {tmp_path.as_posix()}/downloads
  state_path: {tmp_path.as_posix()}/state
""",
    )
    with pytest.raises(ConfigError, match=message):
        load_config(config_path)


def test_empty_room_list_fails_instead_of_waiting_for_input(tmp_path: Path) -> None:
    config_path = write_config(tmp_path / "empty.yaml", "rooms: []\n")
    with pytest.raises(ConfigError, match="没有启用"):
        load_config(config_path, validate_storage=False)


def test_daemon_can_load_empty_room_snapshot_for_web_hot_add(tmp_path: Path) -> None:
    config_path = write_config(tmp_path / "empty.yaml", "rooms: []\n")
    config = load_config(
        config_path,
        validate_storage=False,
        require_enabled_rooms=False,
    )
    assert config.rooms == ()


def test_cookie_priority_and_redaction(tmp_path: Path) -> None:
    secret = tmp_path / "cookie"
    secret.write_text("ttwid=file-secret", encoding="utf-8")
    value, source = load_cookie(
        "ttwid=config-secret",
        {
            "DOUYIN_COOKIE": "ttwid=env-secret",
            "DOUYIN_COOKIE_FILE": str(secret),
        },
    )
    assert value == "ttwid=file-secret"
    assert source == "file"
    assert "file-secret" not in redact_secret(value)


def test_cookie_rejects_multiline_header_injection() -> None:
    with pytest.raises(ConfigError, match="格式异常"):
        load_cookie("", {"DOUYIN_COOKIE": "ttwid=ok\nAuthorization: bad"})


def test_remux_configuration_is_typed_and_bounded(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path / "remux.yaml",
        f"""
rooms:
  - url: https://live.douyin.com/123
recorder:
  remux_to_mp4: true
  remux_workers: 2
  delete_source_after_remux: false
storage:
  path: {tmp_path.as_posix()}/downloads
  state_path: {tmp_path.as_posix()}/state
  min_free_gb: 0.1
""",
    )
    config = load_config(config_path)
    assert config.recorder.remux_to_mp4 is True
    assert config.recorder.remux_workers == 2
    assert config.recorder.delete_source_after_remux is False
