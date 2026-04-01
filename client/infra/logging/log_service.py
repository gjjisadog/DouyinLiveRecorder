"""Shared helpers for client log levels and sources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

LEVEL_ALL = "all"
LEVEL_INFO = "info"
LEVEL_WARNING = "warning"
LEVEL_ERROR = "error"
LEVEL_DEBUG = "debug"

SOURCE_ALL = "all"
SOURCE_SYSTEM = "system"
SOURCE_MAIN_WINDOW = "main_window"
SOURCE_TASKS = "tasks"
SOURCE_SETTINGS = "settings"
SOURCE_LOGS = "logs"
SOURCE_RECORD = "record"
SOURCE_CONFIG = "config"
SOURCE_TASK_STORE = "task_store"
SOURCE_HISTORY = "history"
SOURCE_SCHEDULER = "scheduler"
SOURCE_NOTIFICATION = "notification"

LEVEL_LABELS: dict[str, str] = {
    LEVEL_ALL: "全部级别",
    LEVEL_INFO: "信息",
    LEVEL_WARNING: "警告",
    LEVEL_ERROR: "错误",
    LEVEL_DEBUG: "调试",
}

SOURCE_LABELS: dict[str, str] = {
    SOURCE_ALL: "全部来源",
    SOURCE_SYSTEM: "系统",
    SOURCE_MAIN_WINDOW: "主窗口",
    SOURCE_TASKS: "任务页",
    SOURCE_SETTINGS: "设置页",
    SOURCE_LOGS: "日志页",
    SOURCE_RECORD: "录制内核",
    SOURCE_CONFIG: "配置服务",
    SOURCE_TASK_STORE: "任务存储",
    SOURCE_HISTORY: "历史记录",
    SOURCE_SCHEDULER: "调度器",
    SOURCE_NOTIFICATION: "通知服务",
}

SOURCE_PREFIXES: dict[str, str] = {
    "[主窗口]": SOURCE_MAIN_WINDOW,
    "[任务]": SOURCE_TASKS,
    "[设置]": SOURCE_SETTINGS,
    "[日志]": SOURCE_LOGS,
    "[录制]": SOURCE_RECORD,
    "[配置]": SOURCE_CONFIG,
    "[任务存储]": SOURCE_TASK_STORE,
    "[历史]": SOURCE_HISTORY,
    "[调度]": SOURCE_SCHEDULER,
    "[通知]": SOURCE_NOTIFICATION,
    "[系统]": SOURCE_SYSTEM,
}

KNOWN_SOURCES: tuple[str, ...] = (
    SOURCE_SYSTEM,
    SOURCE_MAIN_WINDOW,
    SOURCE_TASKS,
    SOURCE_SETTINGS,
    SOURCE_LOGS,
    SOURCE_RECORD,
    SOURCE_CONFIG,
    SOURCE_TASK_STORE,
    SOURCE_HISTORY,
    SOURCE_SCHEDULER,
    SOURCE_NOTIFICATION,
)


@dataclass(slots=True, frozen=True)
class LogPayload:
    message: str
    level: str
    source: str


LogHandler = Callable[[str, str | None, str | None], None]


class LogEmitterMixin:
    def __init__(self, log_handler: LogHandler | None = None, log_source: str = SOURCE_SYSTEM) -> None:
        self._log_handler = log_handler
        self._log_source = log_source

    def set_log_handler(self, handler: LogHandler | None) -> None:
        self._log_handler = handler

    def _emit_log(self, message: str, level: str = LEVEL_INFO, source: str | None = None) -> None:
        if self._log_handler is None:
            return
        self._log_handler(message, level, source or self._log_source)


class LogBuffer:
    def __init__(self) -> None:
        self.records: list[LogPayload] = []

    def handle(self, message: str, level: str | None = None, source: str | None = None) -> None:
        self.records.append(LogService.parse(message=message, level=level, source=source))

    def flush_to(self, handler: LogHandler) -> None:
        for record in self.records:
            handler(record.message, record.level, record.source)
        self.records.clear()


class LogService:
    @staticmethod
    def normalize_level(level: str | None) -> str:
        if level in {LEVEL_INFO, LEVEL_WARNING, LEVEL_ERROR, LEVEL_DEBUG}:
            return level
        return LEVEL_INFO

    @staticmethod
    def normalize_source(source: str | None) -> str:
        if source in KNOWN_SOURCES:
            return source
        return SOURCE_SYSTEM

    @staticmethod
    def level_label(level: str) -> str:
        return LEVEL_LABELS.get(level, level.upper())

    @staticmethod
    def source_label(source: str) -> str:
        return SOURCE_LABELS.get(source, source)

    @staticmethod
    def iter_sources() -> tuple[str, ...]:
        return KNOWN_SOURCES

    @staticmethod
    def infer_level(message: str) -> str:
        normalized = message.lower()
        if any(token in normalized for token in ("[error]", " error", "failed", "失败", "异常", "错误")):
            return LEVEL_ERROR
        if any(token in normalized for token in ("[warning]", " warning", "warn", "警告")):
            return LEVEL_WARNING
        if any(token in normalized for token in ("[debug]", " debug", "调试")):
            return LEVEL_DEBUG
        return LEVEL_INFO

    @staticmethod
    def infer_source(message: str) -> str:
        stripped = message.strip()
        for prefix, source in SOURCE_PREFIXES.items():
            if stripped.startswith(prefix):
                return source
        return SOURCE_SYSTEM

    @staticmethod
    def strip_legacy_prefix(message: str) -> str:
        stripped = message.strip()
        for prefix in SOURCE_PREFIXES:
            if stripped.startswith(prefix):
                return stripped.removeprefix(prefix).lstrip(" ：:-")
        return stripped

    @classmethod
    def parse(cls, message: str, level: str | None = None, source: str | None = None) -> LogPayload:
        normalized_message = cls.strip_legacy_prefix(message)
        return LogPayload(
            message=normalized_message,
            level=cls.normalize_level(level or cls.infer_level(normalized_message)),
            source=cls.normalize_source(source or cls.infer_source(message)),
        )
