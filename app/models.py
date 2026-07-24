from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RoomConfig:
    url: str
    name: str = ""
    quality: str = "original"
    enabled: bool = True


@dataclass(frozen=True)
class RecorderConfig:
    format: str = "ts"
    segment_seconds: int = 1800
    poll_seconds: int = 120
    max_concurrent_checks: int = 3
    stream_protocol: str = "auto"


@dataclass(frozen=True)
class StorageConfig:
    path: Path = Path("/data/downloads")
    state_path: Path = Path("/data/state")
    min_free_gb: float = 10.0


@dataclass(frozen=True)
class ProxyConfig:
    url: str = ""


@dataclass(frozen=True)
class NotificationConfig:
    enabled: bool = False


@dataclass(frozen=True)
class AppConfig:
    rooms: tuple[RoomConfig, ...]
    recorder: RecorderConfig = field(default_factory=RecorderConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    cookie: str = field(default="", repr=False)
