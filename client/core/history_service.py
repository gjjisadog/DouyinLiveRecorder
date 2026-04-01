"""History service for the desktop client."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from client.core.enums import Platform, TaskStatus
from client.core.models import HistoryRecord, RecordSession, RecordTask
from client.core.notification_service import NotificationService
from client.infra.logging.log_service import LEVEL_INFO, LEVEL_WARNING, LogEmitterMixin, LogHandler, SOURCE_HISTORY
from client.infra.storage.json_store import JsonStore

HistoryListener = Callable[[], None]


class HistoryService(LogEmitterMixin):
    def __init__(
        self,
        file_path: Path,
        log_handler: LogHandler | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        super().__init__(log_handler=log_handler, log_source=SOURCE_HISTORY)
        self.file_path = file_path
        self.store = JsonStore(file_path)
        self.notification_service = notification_service
        self.records: list[HistoryRecord] = []
        self._active_record_index: dict[str, int] = {}
        self._listeners: list[HistoryListener] = []
        self.load()

    def register_listener(self, listener: HistoryListener) -> None:
        self._listeners.append(listener)

    def load(self) -> None:
        payload = self.store.load(default={}, on_error=self._handle_store_error)
        items = payload.get("records", []) if isinstance(payload, dict) else []
        records: list[HistoryRecord] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            try:
                records.append(self._deserialize_record(item))
            except (TypeError, ValueError) as exc:
                record_id = item.get("task_id") or f"record-{index:03d}"
                self._emit_log(f"已跳过损坏的历史记录 {record_id}：{exc}", LEVEL_WARNING)
        self.records = records
        self._active_record_index = {
            record.task_id: index
            for index, record in enumerate(self.records)
            if record.status == TaskStatus.RUNNING and record.finished_at is None
        }

    def save(self) -> None:
        payload = {
            "version": 1,
            "records": [self._serialize_record(record) for record in self.records],
        }
        self.store.save(payload)

    def list_all(self) -> list[HistoryRecord]:
        return list(
            sorted(
                self.records,
                key=lambda record: (
                    record.started_at or datetime.min,
                    record.finished_at or datetime.min,
                ),
                reverse=True,
            )
        )

    def clear(self) -> None:
        self.records.clear()
        self._active_record_index.clear()
        self.save()
        self._emit_log("已清空历史记录。", LEVEL_INFO)
        self._notify_changed()

    def record_started(self, task: RecordTask, session: RecordSession) -> None:
        record = HistoryRecord(
            task_id=task.task_id,
            status=TaskStatus.RUNNING,
            platform=task.platform,
            display_name=task.anchor_name or task.display_name,
            title=task.title,
            file_path=session.output_file,
            started_at=session.started_at,
            finished_at=None,
            error_message="",
        )
        self.records.append(record)
        self._active_record_index[task.task_id] = len(self.records) - 1
        self.save()
        if self.notification_service is not None:
            self.notification_service.notify_task_started(task)
        self._emit_log(f"已写入运行历史：{task.task_id}", LEVEL_INFO)
        self._notify_changed()

    def record_finished(self, task: RecordTask, status: TaskStatus, error_message: str = "") -> None:
        now = datetime.now()
        index = self._active_record_index.pop(task.task_id, None)
        if index is None:
            record = HistoryRecord(
                task_id=task.task_id,
                status=status,
                platform=task.platform,
                display_name=task.anchor_name or task.display_name,
                title=task.title,
                file_path=task.output_path,
                started_at=None,
                finished_at=now,
                error_message=error_message or task.last_error,
            )
            self.records.append(record)
        else:
            record = self.records[index]
            record.status = status
            record.platform = task.platform
            record.display_name = task.anchor_name or task.display_name
            record.title = task.title
            record.file_path = task.output_path or record.file_path
            record.finished_at = now
            record.error_message = error_message or task.last_error
        self.save()
        if self.notification_service is not None:
            self.notification_service.notify_task_finished(task, status, error_message or task.last_error)
        self._emit_log(f"已更新历史记录：{task.task_id} -> {status.value}", LEVEL_INFO)
        self._notify_changed()

    def _notify_changed(self) -> None:
        for listener in list(self._listeners):
            listener()

    def _serialize_record(self, record: HistoryRecord) -> dict[str, str | None]:
        return {
            "task_id": record.task_id,
            "status": record.status.value,
            "platform": record.platform.value,
            "display_name": record.display_name,
            "title": record.title,
            "file_path": str(record.file_path) if record.file_path is not None else None,
            "started_at": record.started_at.isoformat() if record.started_at is not None else None,
            "finished_at": record.finished_at.isoformat() if record.finished_at is not None else None,
            "error_message": record.error_message,
        }

    def _deserialize_record(self, item: dict) -> HistoryRecord:
        return HistoryRecord(
            task_id=str(item.get("task_id") or ""),
            status=self._parse_status(str(item.get("status") or TaskStatus.STOPPED.value)),
            platform=self._parse_platform(str(item.get("platform") or Platform.UNKNOWN.value)),
            display_name=str(item.get("display_name") or ""),
            title=str(item.get("title") or ""),
            file_path=Path(item["file_path"]) if item.get("file_path") else None,
            started_at=datetime.fromisoformat(item["started_at"]) if item.get("started_at") else None,
            finished_at=datetime.fromisoformat(item["finished_at"]) if item.get("finished_at") else None,
            error_message=str(item.get("error_message") or ""),
        )

    def _parse_status(self, raw_status: str) -> TaskStatus:
        try:
            return TaskStatus(raw_status)
        except ValueError:
            return TaskStatus.STOPPED

    def _parse_platform(self, raw_platform: str) -> Platform:
        try:
            return Platform(raw_platform)
        except ValueError:
            return Platform.UNKNOWN

    def _handle_store_error(self, exc: Exception, path: Path, backup_path: Path | None) -> None:
        suffix = f"，已备份到 {backup_path}" if backup_path is not None else ""
        self._emit_log(f"读取历史记录失败：{path}，将忽略损坏内容并继续启动。{exc}{suffix}", LEVEL_WARNING)
