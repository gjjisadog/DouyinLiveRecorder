from __future__ import annotations

import argparse
import configparser
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

from .config import DOUYIN_HOSTS

QUALITY_MAP = {
    "原画": "original",
    "蓝光": "original",
    "超清": "uhd",
    "高清": "hd",
    "标清": "sd",
    "流畅": "ld",
}


def read_douyin_rooms(path: Path) -> list[dict[str, object]]:
    rooms: list[dict[str, object]] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        parts = [part.strip() for part in line.split(",", 2)]
        url_index = next(
            (index for index, value in enumerate(parts) if value.startswith(("http://", "https://"))),
            -1,
        )
        if url_index < 0:
            continue
        url = parts[url_index]
        host = urlparse(url).netloc.lower().split(":", 1)[0]
        if host not in DOUYIN_HOSTS:
            continue
        quality = QUALITY_MAP.get(parts[0], "original") if url_index > 0 else "original"
        name = parts[2] if len(parts) > 2 else ""
        rooms.append(
            {
                "url": url,
                "name": name,
                "quality": quality,
                "enabled": True,
            }
        )
    return rooms


def read_legacy_settings(path: Path) -> tuple[str, str]:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(path, encoding="utf-8-sig")
    cookie = parser.get("Cookie", "抖音cookie", fallback="").strip()
    proxy = parser.get("录制设置", "代理地址", fallback="").strip()
    return cookie, proxy


def migrate(
    url_config: Path,
    legacy_config: Path,
    output_config: Path,
    output_cookie: Path,
    cookie_uid: int | None = None,
) -> int:
    if cookie_uid is not None and cookie_uid < 0:
        raise ValueError("cookie_uid 不能为负数")
    rooms = read_douyin_rooms(url_config)
    if not rooms:
        raise ValueError("旧配置中没有启用的抖音直播间")
    cookie, proxy = read_legacy_settings(legacy_config)
    payload = {
        "rooms": rooms,
        "recorder": {
            "format": "ts",
            "segment_seconds": 1800,
            "poll_seconds": 120,
            "max_concurrent_checks": 3,
            "stream_protocol": "auto",
            "remux_to_mp4": False,
            "remux_workers": 1,
            "delete_source_after_remux": False,
        },
        "storage": {
            "path": "/data/downloads",
            "state_path": "/data/state",
            "min_free_gb": 10,
        },
        "proxy": {"url": proxy},
        "cookie": {"value": ""},
        "notifications": {"enabled": False},
    }
    output_config.parent.mkdir(parents=True, exist_ok=True)
    output_config.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    output_cookie.parent.mkdir(parents=True, exist_ok=True)
    output_cookie.write_text(cookie, encoding="utf-8")
    if os.name != "nt":
        output_cookie.chmod(0o600)
        if cookie_uid is not None:
            os.chown(output_cookie, cookie_uid, cookie_uid)
            output_cookie.chmod(0o400)
    return len(rooms)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy INI files to Douyin daemon YAML")
    parser.add_argument("--url-config", required=True, type=Path)
    parser.add_argument("--legacy-config", required=True, type=Path)
    parser.add_argument("--output-config", required=True, type=Path)
    parser.add_argument("--output-cookie", required=True, type=Path)
    parser.add_argument(
        "--cookie-uid",
        type=int,
        help="When migrating as root in Docker, make the Secret readable only by this UID",
    )
    args = parser.parse_args(argv)
    try:
        room_count = migrate(
            args.url_config,
            args.legacy_config,
            args.output_config,
            args.output_cookie,
            args.cookie_uid,
        )
    except (OSError, configparser.Error, ValueError) as exc:
        print(f"migration_failed error={exc}", file=sys.stderr)
        return 2
    print(f"migration_completed rooms={room_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
