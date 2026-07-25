from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.migrate_legacy import migrate, read_douyin_rooms


def test_read_douyin_rooms_filters_platforms_and_comments(tmp_path: Path) -> None:
    path = tmp_path / "URL_config.ini"
    path.write_text(
        "\n".join(
            [
                "#原画,https://live.douyin.com/disabled,disabled",
                "高清,https://live.douyin.com/123,主播A",
                "https://v.douyin.com/AbCd/",
                "原画,https://www.tiktok.com/@demo/live,TikTok",
            ]
        ),
        encoding="utf-8",
    )
    rooms = read_douyin_rooms(path)
    assert len(rooms) == 2
    assert rooms[0]["quality"] == "hd"
    assert rooms[0]["name"] == "主播A"
    assert rooms[1]["quality"] == "original"


def test_migrate_writes_yaml_and_separate_cookie(tmp_path: Path) -> None:
    urls = tmp_path / "URL_config.ini"
    urls.write_text("原画,https://live.douyin.com/123,主播A\n", encoding="utf-8")
    legacy = tmp_path / "config.ini"
    legacy.write_text(
        """
[录制设置]
代理地址 = http://127.0.0.1:7890
[Cookie]
抖音cookie = ttwid=secret-value
""".strip(),
        encoding="utf-8",
    )
    output = tmp_path / "douyin.yaml"
    secret = tmp_path / "douyin_cookie"
    assert migrate(urls, legacy, output, secret) == 1
    payload = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert payload["rooms"][0]["url"] == "https://live.douyin.com/123"
    assert payload["cookie"]["value"] == ""
    assert payload["proxy"]["url"] == "http://127.0.0.1:7890"
    assert secret.read_text(encoding="utf-8") == "ttwid=secret-value"
    assert "secret-value" not in output.read_text(encoding="utf-8")


def test_migrate_rejects_negative_cookie_uid(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cookie_uid"):
        migrate(
            tmp_path / "URL_config.ini",
            tmp_path / "config.ini",
            tmp_path / "douyin.yaml",
            tmp_path / "cookie",
            cookie_uid=-1,
        )
