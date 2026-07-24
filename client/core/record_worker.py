"""Recording worker."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from client.core.enums import TaskStatus
from client.core.ffmpeg_service import FfmpegService
from client.core.history_service import HistoryService
from client.core.models import AppConfig, RecordSession, RecordTask
from client.core.stream_resolver import StreamResolver
from client.infra.logging.log_service import (
    LEVEL_DEBUG,
    LEVEL_ERROR,
    LEVEL_INFO,
    LEVEL_WARNING,
    LogEmitterMixin,
    LogHandler,
    SOURCE_RECORD,
)


class RecordWorker(LogEmitterMixin):
    def __init__(
        self,
        stream_resolver: StreamResolver,
        ffmpeg_service: FfmpegService,
        config: AppConfig | None = None,
        log_handler: LogHandler | None = None,
        history_service: HistoryService | None = None,
    ) -> None:
        super().__init__(log_handler=log_handler, log_source=SOURCE_RECORD)
        self.stream_resolver = stream_resolver
        self.ffmpeg_service = ffmpeg_service
        self.config = config or AppConfig()
        self.history_service = history_service
        self.sessions: dict[str, RecordSession] = {}
        self.stream_resolver.set_log_handler(log_handler)
        self.ffmpeg_service.set_log_handler(log_handler)

    def set_log_handler(self, handler: LogHandler | None) -> None:
        super().set_log_handler(handler)
        self.stream_resolver.set_log_handler(handler)
        self.ffmpeg_service.set_log_handler(handler)

    def start(self, task: RecordTask, config: AppConfig | None = None) -> RecordSession:
        effective_config = config or self.config
        task.last_error = ""
        task.status = TaskStatus.PENDING
        self._emit_log(f"开始启动任务 {task.task_id}。", LEVEL_INFO)
        stream = self.stream_resolver.resolve_task(task, effective_config)
        if not stream.is_live and not task.url.lower().endswith((".m3u8", ".flv")):
            task.status = TaskStatus.IDLE
            self._emit_log(f"任务 {task.task_id} 当前未开播，已取消启动。", LEVEL_WARNING)
            raise RuntimeError(f"Task is not live: {task.url}")

        command, output_file = self.ffmpeg_service.build_command(task, stream, effective_config)
        session = self.ffmpeg_service.start_record(task, command, output_file)
        task.output_path = output_file
        task.title = stream.title or task.title
        task.status = TaskStatus.RUNNING
        self.sessions[task.task_id] = session
        if self.history_service is not None:
            self.history_service.record_started(task, session)
        self._emit_log(f"任务 {task.task_id} 已进入录制中状态。", LEVEL_INFO)
        return session

    def stop(self, task: RecordTask) -> None:
        session = self.sessions.get(task.task_id)
        if session is None:
            self._emit_log(f"任务 {task.task_id} 当前没有活动录制会话。", LEVEL_DEBUG)
        else:
            self._emit_log(f"开始停止任务 {task.task_id}。", LEVEL_INFO)
            self._sync_output_path(task, session)

        self.ffmpeg_service.stop_record(task)
        task.status = TaskStatus.STOPPED
        self.sessions.pop(task.task_id, None)
        if self.history_service is not None:
            self.history_service.record_finished(task, TaskStatus.STOPPED)
        self._emit_log(f"任务 {task.task_id} 已停止。", LEVEL_INFO)

    def sync_task(self, task: RecordTask) -> bool:
        session = self.sessions.get(task.task_id)
        if session is None:
            return False

        output_path_changed = self._sync_output_path(task, session)
        if self.ffmpeg_service.is_session_over_size_limit(session, self.config):
            self._rollover_task(task, session)
            return True

        return_code = self.ffmpeg_service.poll_record(task.task_id)
        if return_code is None:
            if task.status != TaskStatus.RUNNING:
                task.status = TaskStatus.RUNNING
                return True
            return output_path_changed

        self.sessions.pop(task.task_id, None)
        self._sync_output_path(task, session)
        if return_code == 0:
            if task.status != TaskStatus.STOPPED:
                task.status = TaskStatus.COMPLETED
                if self.history_service is not None:
                    self.history_service.record_finished(task, TaskStatus.COMPLETED)
                self._emit_log(f"任务 {task.task_id} 的录制进程已退出。", LEVEL_INFO)
                return True
            return output_path_changed

        task.status = TaskStatus.FAILED
        task.last_error = f"ffmpeg exited with code {return_code}"
        if self.history_service is not None:
            self.history_service.record_finished(task, TaskStatus.FAILED, task.last_error)
        self._emit_log(f"任务 {task.task_id} 的录制进程异常退出，返回码 {return_code}。", LEVEL_ERROR)
        return True

    def sync_tasks(self, tasks: Iterable[RecordTask]) -> bool:
        changed = False
        for task in tasks:
            changed = self.sync_task(task) or changed
        return changed

    def _rollover_task(self, task: RecordTask, session: RecordSession) -> None:
        previous_output = session.output_file
        self._emit_log(
            f"任务 {task.task_id} 的录制文件已达到单文件上限，准备自动切换新文件。",
            LEVEL_INFO,
        )
        self.ffmpeg_service.stop_record(task)
        self.sessions.pop(task.task_id, None)
        self._sync_output_path(task, session)
        if self.history_service is not None:
            self.history_service.record_finished(task, TaskStatus.COMPLETED)

        try:
            self.start(task, config=self.config)
            self._emit_log(
                f"任务 {task.task_id} 已自动切换到新的录制文件。上一段：{previous_output}",
                LEVEL_INFO,
            )
        except Exception as exc:
            task.last_error = str(exc)
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.FAILED
            self._emit_log(f"任务 {task.task_id} 在按大小切段后重启失败：{exc}", LEVEL_ERROR)

    def _sync_output_path(self, task: RecordTask, session: RecordSession | None) -> bool:
        if session is None:
            return False
        resolved_output = self.ffmpeg_service.resolve_output_file(session.output_file)
        if not isinstance(resolved_output, Path):
            return False
        if task.output_path == resolved_output:
            return False
        task.output_path = resolved_output
        return True
