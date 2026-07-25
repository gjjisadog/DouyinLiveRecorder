from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import yaml

from .config import ConfigError, QUALITY_ALIASES, load_config, normalize_douyin_url


DEFAULT_DOCUMENT: dict[str, Any] = {
    "rooms": [],
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
    "proxy": {"url": ""},
    "cookie": {"value": ""},
    "notifications": {"enabled": False},
}


@dataclass(frozen=True)
class ManagedRoom:
    index: int
    url: str
    name: str
    quality: str
    enabled: bool


class YamlConfigStore:
    """Serialize Web mutations to one validated, atomically replaced YAML file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def ensure_file(self) -> None:
        with self._lock:
            if self.path.exists():
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._write_validated(dict(DEFAULT_DOCUMENT))

    def _read_document_unlocked(self) -> dict[str, Any]:
        self.ensure_file()
        try:
            payload = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise ConfigError(f"配置文件读取失败: {self.path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ConfigError("根配置必须是 YAML 对象")
        rooms = payload.get("rooms")
        if not isinstance(rooms, list):
            raise ConfigError("rooms 必须是列表")
        return payload

    def read_document(self) -> dict[str, Any]:
        with self._lock:
            return self._read_document_unlocked()

    def _assert_cookie_is_secret_only(self, document: dict[str, Any]) -> None:
        cookie = document.get("cookie")
        if isinstance(cookie, dict) and str(cookie.get("value") or "").strip():
            raise ConfigError(
                "Web 不会读取或改写明文 cookie.value；请先迁移到 DOUYIN_COOKIE_FILE"
            )

    @staticmethod
    def _normalized_room(
        *, url: str, name: str = "", quality: str = "original", enabled: bool = True
    ) -> dict[str, Any]:
        canonical_url, _ = normalize_douyin_url(url)
        normalized_quality = quality.strip().lower() or "original"
        if normalized_quality not in QUALITY_ALIASES:
            raise ConfigError("画质必须是 original/uhd/hd/sd/ld")
        normalized_name = name.strip()
        if len(normalized_name) > 100:
            raise ConfigError("主播名称不能超过 100 个字符")
        return {
            "url": canonical_url,
            "name": normalized_name,
            "quality": normalized_quality,
            "enabled": bool(enabled),
        }

    def list_rooms(self) -> tuple[ManagedRoom, ...]:
        document = self.read_document()
        result: list[ManagedRoom] = []
        for index, raw in enumerate(document["rooms"]):
            if not isinstance(raw, dict):
                raise ConfigError(f"rooms[{index}] 必须是 YAML 对象")
            room = self._normalized_room(
                url=str(raw.get("url") or ""),
                name=str(raw.get("name") or ""),
                quality=str(raw.get("quality") or "original"),
                enabled=raw.get("enabled", True) is True,
            )
            result.append(ManagedRoom(index=index, **room))
        return tuple(result)

    def recorder_settings(self) -> dict[str, Any]:
        document = self.read_document()
        recorder = document.get("recorder")
        if not isinstance(recorder, dict):
            return {}
        allowed = (
            "format",
            "segment_seconds",
            "poll_seconds",
            "max_concurrent_checks",
            "stream_protocol",
            "remux_to_mp4",
        )
        return {key: recorder.get(key) for key in allowed}

    def _mutate(self, mutation: Callable[[list[Any]], None]) -> None:
        with self._lock:
            document = self._read_document_unlocked()
            self._assert_cookie_is_secret_only(document)
            rooms = document["rooms"]
            mutation(rooms)
            self._write_validated(document)

    def add(
        self, *, url: str, name: str = "", quality: str = "original", enabled: bool = True
    ) -> None:
        room = self._normalized_room(url=url, name=name, quality=quality, enabled=enabled)
        self._mutate(lambda rooms: rooms.append(room))

    def update(
        self,
        index: int,
        *,
        url: str,
        name: str = "",
        quality: str = "original",
        enabled: bool = True,
    ) -> None:
        room = self._normalized_room(url=url, name=name, quality=quality, enabled=enabled)

        def mutation(rooms: list[Any]) -> None:
            if index < 0 or index >= len(rooms):
                raise IndexError("房间不存在")
            rooms[index] = room

        self._mutate(mutation)

    def toggle(self, index: int) -> None:
        def mutation(rooms: list[Any]) -> None:
            if index < 0 or index >= len(rooms) or not isinstance(rooms[index], dict):
                raise IndexError("房间不存在")
            rooms[index]["enabled"] = not bool(rooms[index].get("enabled", True))

        self._mutate(mutation)

    def delete(self, index: int) -> None:
        def mutation(rooms: list[Any]) -> None:
            if index < 0 or index >= len(rooms):
                raise IndexError("房间不存在")
            del rooms[index]

        self._mutate(mutation)

    def _write_validated(self, document: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{uuid4().hex}.tmp")
        try:
            with temporary.open("x", encoding="utf-8", newline="\n") as stream:
                yaml.safe_dump(
                    document,
                    stream,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
                stream.flush()
                os.fsync(stream.fileno())
            load_config(
                temporary,
                validate_storage=False,
                require_enabled_rooms=False,
            )
            os.replace(temporary, self.path)
        except Exception:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise
