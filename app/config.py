from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import yaml

from .models import (
    AppConfig,
    NotificationConfig,
    ProxyConfig,
    RecorderConfig,
    RoomConfig,
    StorageConfig,
)

QUALITY_ALIASES = {
    "original": "OD",
    "od": "OD",
    "uhd": "UHD",
    "hd": "HD",
    "sd": "SD",
    "ld": "LD",
}
DOUYIN_HOSTS = {"live.douyin.com", "www.douyin.com", "douyin.com", "v.douyin.com"}


class ConfigError(ValueError):
    pass


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"{field} 必须是 YAML 对象")
    return value


def _bool(value: Any, field: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ConfigError(f"{field} 必须是 true 或 false")
    return value


def _int_range(value: Any, field: str, default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{field} 必须是整数")
    if not minimum <= value <= maximum:
        raise ConfigError(f"{field} 必须在 {minimum} 到 {maximum} 之间")
    return value


def _float_range(value: Any, field: str, default: float, minimum: float, maximum: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{field} 必须是数字")
    result = float(value)
    if not minimum <= result <= maximum:
        raise ConfigError(f"{field} 必须在 {minimum} 到 {maximum} 之间")
    return result


def normalize_douyin_url(url: str) -> tuple[str, str]:
    raw = url.strip()
    parsed = urlparse(raw)
    host = parsed.netloc.lower().split(":", 1)[0]
    if parsed.scheme not in {"http", "https"} or host not in DOUYIN_HOSTS:
        raise ConfigError(f"rooms.url 不是支持的抖音地址: {raw}")
    parts = [part for part in parsed.path.split("/") if part]
    if host == "live.douyin.com" and parts:
        room_id = parts[0]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", room_id):
            raise ConfigError(f"rooms.url 包含非法直播间标识: {raw}")
        return f"https://live.douyin.com/{room_id}", f"room:{room_id}"
    if host in {"www.douyin.com", "douyin.com"} and len(parts) >= 2 and parts[0] == "user":
        return f"https://www.douyin.com/user/{parts[1]}", f"user:{parts[1]}"
    if host == "v.douyin.com" and parts:
        return f"https://v.douyin.com/{parts[0]}/", f"short:{parts[0].lower()}"
    raise ConfigError(f"rooms.url 无法识别直播间或主播标识: {raw}")


def redact_secret(value: str) -> str:
    if not value:
        return "<empty>"
    if len(value) <= 8:
        return "***"
    return f"{value[:3]}***{value[-3:]}"


def load_cookie(
    config_value: str = "",
    environ: dict[str, str] | None = None,
    read_text: Callable[[Path], str] | None = None,
) -> tuple[str, str]:
    env = os.environ if environ is None else environ
    reader = (lambda path: path.read_text(encoding="utf-8")) if read_text is None else read_text
    cookie_file = env.get("DOUYIN_COOKIE_FILE", "").strip()
    if cookie_file:
        try:
            value = reader(Path(cookie_file)).strip()
        except OSError as exc:
            raise ConfigError(f"DOUYIN_COOKIE_FILE 无法读取: {cookie_file}: {exc}") from exc
        source = "file"
    elif env.get("DOUYIN_COOKIE", "").strip():
        value = env["DOUYIN_COOKIE"].strip()
        source = "environment"
    else:
        value = config_value.strip()
        source = "config"
    if value and ("=" not in value or "\n" in value or "\r" in value):
        raise ConfigError("抖音 Cookie 格式异常，应为 name=value; name2=value2")
    return value, source


def _ensure_writable_directory(path: Path, field: str) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
        marker = path / ".write-test"
        marker.touch(exist_ok=True)
        marker.unlink()
    except OSError as exc:
        raise ConfigError(f"{field} 不可写: {path}: {exc}") from exc


def load_config(
    path: str | Path,
    *,
    validate_storage: bool = True,
    require_enabled_rooms: bool = True,
) -> AppConfig:
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigError(f"配置文件不存在: {config_path}")
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"配置文件读取失败: {config_path}: {exc}") from exc
    root = _mapping(payload, "根配置")

    raw_rooms = root.get("rooms")
    if not isinstance(raw_rooms, list):
        raise ConfigError("rooms 必须是列表")
    rooms: list[RoomConfig] = []
    seen: set[str] = set()
    for index, raw_room in enumerate(raw_rooms):
        room = _mapping(raw_room, f"rooms[{index}]")
        enabled = _bool(room.get("enabled"), f"rooms[{index}].enabled", True)
        url = room.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ConfigError(f"rooms[{index}].url 必须是非空字符串")
        canonical_url, identity = normalize_douyin_url(url)
        quality_value = room.get("quality", "original")
        if not isinstance(quality_value, str) or quality_value.lower() not in QUALITY_ALIASES:
            raise ConfigError(f"rooms[{index}].quality 必须是 original/uhd/hd/sd/ld")
        name = room.get("name", "")
        if not isinstance(name, str):
            raise ConfigError(f"rooms[{index}].name 必须是字符串")
        if enabled and identity not in seen:
            seen.add(identity)
            rooms.append(RoomConfig(canonical_url, name.strip(), quality_value.lower(), True))
    if require_enabled_rooms and not rooms:
        raise ConfigError("rooms 中没有启用的抖音直播间")

    recorder = _mapping(root.get("recorder"), "recorder")
    record_format = recorder.get("format", "ts")
    if not isinstance(record_format, str) or record_format.lower() != "ts":
        raise ConfigError("recorder.format 当前 Docker daemon 仅支持 ts")
    protocol = recorder.get("stream_protocol", "auto")
    if protocol not in {"auto", "flv", "hls"}:
        raise ConfigError("recorder.stream_protocol 必须是 auto、flv 或 hls")
    recorder_config = RecorderConfig(
        format="ts",
        segment_seconds=_int_range(
            recorder.get("segment_seconds"), "recorder.segment_seconds", 1800, 60, 86400
        ),
        poll_seconds=_int_range(recorder.get("poll_seconds"), "recorder.poll_seconds", 120, 10, 3600),
        max_concurrent_checks=_int_range(
            recorder.get("max_concurrent_checks"), "recorder.max_concurrent_checks", 3, 1, 32
        ),
        stream_protocol=protocol,
        remux_to_mp4=_bool(recorder.get("remux_to_mp4"), "recorder.remux_to_mp4", False),
        remux_workers=_int_range(
            recorder.get("remux_workers"), "recorder.remux_workers", 1, 1, 4
        ),
        delete_source_after_remux=_bool(
            recorder.get("delete_source_after_remux"),
            "recorder.delete_source_after_remux",
            False,
        ),
    )

    storage = _mapping(root.get("storage"), "storage")
    storage_path = Path(str(storage.get("path", "/data/downloads"))).expanduser()
    state_path = Path(str(storage.get("state_path", "/data/state"))).expanduser()
    storage_config = StorageConfig(
        path=storage_path,
        state_path=state_path,
        min_free_gb=_float_range(storage.get("min_free_gb"), "storage.min_free_gb", 10.0, 0.1, 10240.0),
    )
    if validate_storage:
        _ensure_writable_directory(storage_path, "storage.path")
        _ensure_writable_directory(state_path, "storage.state_path")

    proxy = _mapping(root.get("proxy"), "proxy")
    proxy_url = proxy.get("url", "")
    if not isinstance(proxy_url, str):
        raise ConfigError("proxy.url 必须是字符串")
    proxy_config = ProxyConfig(
        url=proxy_url.strip(),
    )
    notifications = _mapping(root.get("notifications"), "notifications")
    notification_config = NotificationConfig(
        enabled=_bool(notifications.get("enabled"), "notifications.enabled", False)
    )
    cookie_section = _mapping(root.get("cookie"), "cookie")
    config_cookie = cookie_section.get("value", "")
    if not isinstance(config_cookie, str):
        raise ConfigError("cookie.value 必须是字符串")
    cookie, _ = load_cookie(config_cookie)
    return AppConfig(tuple(rooms), recorder_config, storage_config, proxy_config, notification_config, cookie)
