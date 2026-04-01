"""Automatic polling scheduler."""

from __future__ import annotations

from datetime import datetime, timedelta

from client.core.enums import TaskStatus
from client.core.models import AppConfig
from client.core.record_manager import RecordManager
from client.infra.logging.log_service import LEVEL_DEBUG, LEVEL_INFO, LEVEL_WARNING, LogEmitterMixin, LogHandler, SOURCE_SCHEDULER


class Scheduler(LogEmitterMixin):
    def __init__(
        self,
        record_manager: RecordManager,
        config: AppConfig | None = None,
        log_handler: LogHandler | None = None,
    ) -> None:
        super().__init__(log_handler=log_handler, log_source=SOURCE_SCHEDULER)
        self.record_manager = record_manager
        self.config = config or AppConfig()
        self._running = False
        self._next_run_at: datetime | None = None
        self._last_run_at: datetime | None = None

    @property
    def running(self) -> bool:
        return self._running

    @property
    def interval_seconds(self) -> int:
        return max(int(self.config.loop_seconds or 300), 5)

    def start(self, immediate: bool = True) -> None:
        self._running = True
        now = datetime.now()
        self._next_run_at = now if immediate else now + timedelta(seconds=self.interval_seconds)
        self._emit_log(f"自动巡检已启动，间隔 {self.interval_seconds} 秒。", LEVEL_INFO)

    def stop(self) -> None:
        self._running = False
        self._next_run_at = None
        self._emit_log("自动巡检已暂停。", LEVEL_INFO)

    def trigger_now(self) -> None:
        self._next_run_at = datetime.now()
        self._emit_log("已请求立即执行一次自动巡检。", LEVEL_INFO)

    def seconds_until_next(self, now: datetime | None = None) -> int | None:
        if not self._running or self._next_run_at is None:
            return None
        current = now or datetime.now()
        remaining = int((self._next_run_at - current).total_seconds())
        return max(remaining, 0)

    def tick(self, now: datetime | None = None) -> bool:
        if not self._running:
            return False
        current = now or datetime.now()
        if self._next_run_at is not None and current < self._next_run_at:
            return False
        self._run_cycle(current)
        self._last_run_at = current
        self._next_run_at = current + timedelta(seconds=self.interval_seconds)
        return True

    def _run_cycle(self, now: datetime) -> None:
        sync_changed = self.record_manager.sync_task_states()
        started = 0
        offline = 0
        failed = 0

        for task in self.record_manager.tasks.values():
            if not task.enabled:
                continue
            if task.status in {TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.STOPPED}:
                continue
            try:
                self.record_manager.start_task(task.task_id)
                started += 1
            except Exception as exc:
                task.last_error = str(exc)
                if "not live" in str(exc).lower():
                    offline += 1
                else:
                    failed += 1
                    self._emit_log(f"自动巡检启动任务 {task.task_id} 失败: {exc}", LEVEL_WARNING)

        if started or failed or sync_changed:
            self._emit_log(
                f"自动巡检完成：启动 {started} 个，离线 {offline} 个，失败 {failed} 个。",
                LEVEL_INFO,
            )
            return
        self._emit_log(
            f"自动巡检完成：无任务变更，离线 {offline} 个，下一轮 {self.interval_seconds} 秒后执行。",
            LEVEL_DEBUG,
        )
