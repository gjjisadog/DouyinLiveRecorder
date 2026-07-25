"""Core data models."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from client.core.enums import OutputFormat, Platform, TaskStatus


@dataclass(slots=True)
class AppConfig:
    output_dir: Path = Path("downloads")
    output_format: OutputFormat = OutputFormat.TS
    quality: str = "原画"
    max_file_size_gb: float = 1.0
    max_concurrency: int = 3
    loop_seconds: int = 300
    queue_seconds: int = 0
    split_recording: bool = True
    split_seconds: int = 1800
    use_proxy: bool = False
    proxy_url: str = ""
    use_https_recording: bool = False
    folder_by_author: bool = True
    folder_by_time: bool = False
    folder_by_title: bool = False
    filename_include_title: bool = False
    clean_emoji: bool = True
    disk_space_limit_gb: float = 1.0
    convert_to_mp4: bool = True
    convert_to_h264: bool = False
    delete_origin_after_convert: bool = True
    create_time_file: bool = False
    show_source_url: bool = False
    disable_record: bool = False
    custom_script: str = ""
    enable_notifications: bool = False
    notify_channels: str = ""
    douyin_cookie: str = ""
    push_settings: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    authorization: dict[str, str] = field(default_factory=dict)
    credentials: dict[str, str] = field(default_factory=dict)
    proxy_platforms: list[str] = field(default_factory=list)
    extra_proxy_platforms: list[str] = field(default_factory=list)
    minimize_to_tray: bool = True
    close_to_tray: bool = True
    start_on_boot: bool = False
    restore_tasks_on_launch: bool = True
    restore_window_on_launch: bool = True
    legacy_config_path: Path | None = None
    legacy_url_config_path: Path | None = None


@dataclass(slots=True)
class RecordTask:
    task_id: str
    url: str
    platform: Platform = Platform.UNKNOWN
    quality: str = "原画"
    enabled: bool = True
    display_name: str = ""
    anchor_name: str = ""
    title: str = ""
    status: TaskStatus = TaskStatus.IDLE
    output_path: Path | None = None
    last_error: str = ""


@dataclass(slots=True)
class StreamInfo:
    is_live: bool = False
    title: str = ""
    quality: str = ""
    m3u8_url: str = ""
    flv_url: str = ""
    record_url: str = ""
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class RecordSession:
    task_id: str
    started_at: datetime
    process_id: int | None = None
    output_file: Path | None = None
    command: list[str] = field(default_factory=list)


@dataclass(slots=True)
class HistoryRecord:
    task_id: str
    status: TaskStatus
    platform: Platform = Platform.UNKNOWN
    display_name: str = ""
    title: str = ""
    file_path: Path | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str = ""
