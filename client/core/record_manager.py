"""Recording task manager."""

from client.core.enums import TaskStatus
from client.core.models import AppConfig
from client.core.models import RecordTask
from client.core.record_worker import RecordWorker
from client.infra.logging.log_service import LEVEL_DEBUG, LEVEL_INFO, LogEmitterMixin, LogHandler, SOURCE_RECORD


class RecordManager(LogEmitterMixin):
    def __init__(self, worker: RecordWorker, config: AppConfig | None = None, log_handler: LogHandler | None = None) -> None:
        super().__init__(log_handler=log_handler, log_source=SOURCE_RECORD)
        self.worker = worker
        self.config = config
        self.tasks: dict[str, RecordTask] = {}
        self.worker.set_log_handler(log_handler)

    def set_log_handler(self, handler: LogHandler | None) -> None:
        super().set_log_handler(handler)
        self.worker.set_log_handler(handler)

    def add_task(self, task: RecordTask) -> None:
        self.tasks[task.task_id] = task
        self._emit_log(f"录制管理器已接管任务 {task.task_id}。", LEVEL_DEBUG)

    def remove_task(self, task_id: str) -> None:
        task = self.tasks.get(task_id)
        if task is not None and task.status in {TaskStatus.PENDING, TaskStatus.RUNNING}:
            self.worker.stop(task)
        self.tasks.pop(task_id, None)
        self._emit_log(f"录制管理器已移除任务 {task_id}。", LEVEL_INFO)

    def get_task(self, task_id: str) -> RecordTask | None:
        return self.tasks.get(task_id)

    def start_task(self, task_id: str) -> None:
        task = self._require_task(task_id)
        self._emit_log(f"录制管理器收到启动请求：{task_id}。", LEVEL_INFO)
        self.worker.start(task, config=self.config)

    def stop_task(self, task_id: str) -> None:
        task = self._require_task(task_id)
        self._emit_log(f"录制管理器收到停止请求：{task_id}。", LEVEL_INFO)
        self.worker.stop(task)

    def start_all(self) -> None:
        task_ids = [task.task_id for task in self.tasks.values() if task.enabled]
        self._emit_log(f"录制管理器开始批量启动任务，共 {len(task_ids)} 个。", LEVEL_INFO)
        for task in self.tasks.values():
            if task.enabled:
                self.worker.start(task, config=self.config)

    def stop_all(self) -> None:
        active_tasks = [task for task in self.tasks.values() if task.status in {TaskStatus.PENDING, TaskStatus.RUNNING}]
        self._emit_log(f"录制管理器开始批量停止任务，共 {len(active_tasks)} 个。", LEVEL_INFO)
        for task in active_tasks:
            self.worker.stop(task)

    def sync_task_states(self) -> bool:
        changed = self.worker.sync_tasks(self.tasks.values())
        if changed:
            self._emit_log("录制管理器已同步任务运行状态。", LEVEL_DEBUG)
        return changed

    def is_task_running(self, task_id: str) -> bool:
        task = self._require_task(task_id)
        if task.status not in {TaskStatus.PENDING, TaskStatus.RUNNING}:
            return False
        return task.task_id in self.worker.sessions

    def _require_task(self, task_id: str) -> RecordTask:
        return self.tasks[task_id]
