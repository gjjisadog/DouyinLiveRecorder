"""Task view model."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from client.core.enums import Platform, TaskStatus
from client.core.models import RecordTask
from client.core.record_manager import RecordManager
from client.core.task_persistence import TaskPersistenceService
from client.infra.logging.log_service import LEVEL_ERROR, LEVEL_INFO, LEVEL_WARNING

PLATFORM_SEARCH_TERMS: dict[Platform, tuple[str, ...]] = {
    Platform.UNKNOWN: ("未知",),
    Platform.DIRECT: ("直链",),
    Platform.DOUYIN: ("抖音",),
    Platform.TIKTOK: ("tiktok",),
    Platform.KUAISHOU: ("快手",),
    Platform.HUYA: ("虎牙",),
    Platform.DOUYU: ("斗鱼",),
    Platform.YY: ("yy",),
    Platform.BILIBILI: ("bilibili",),
    Platform.NETEASE_CC: ("网易cc",),
    Platform.QIANDUREBO: ("千度热播",),
    Platform.PANDATV: ("pandatv",),
    Platform.BAIDU: ("百度直播",),
    Platform.SHOWROOM: ("showroom",),
    Platform.CHZZK: ("chzzk",),
}

STATUS_SEARCH_TERMS: dict[TaskStatus, tuple[str, ...]] = {
    TaskStatus.IDLE: ("空闲",),
    TaskStatus.PENDING: ("准备中",),
    TaskStatus.RUNNING: ("运行中",),
    TaskStatus.STOPPED: ("已停止",),
    TaskStatus.COMPLETED: ("已完成",),
    TaskStatus.FAILED: ("失败",),
}


@dataclass(slots=True)
class TaskActionResult:
    ok: bool
    message: str
    level: str = LEVEL_INFO
    status_message: str | None = None
    status_timeout: int = 3000
    refresh: bool = False
    selected_task_id: str | None = None
    dialog_title: str | None = None
    dialog_message: str | None = None


@dataclass(slots=True)
class TaskViewModel:
    tasks: list[RecordTask] = field(default_factory=list)

    @classmethod
    def with_demo_data(cls) -> "TaskViewModel":
        return cls(
            tasks=[
                RecordTask(
                    task_id="task-001",
                    url="https://live.douyin.com/example",
                    platform=Platform.DOUYIN,
                    anchor_name="Demo Anchor A",
                    title="Evening Live Test",
                    status=TaskStatus.RUNNING,
                ),
                RecordTask(
                    task_id="task-002",
                    url="https://www.tiktok.com/@example/live",
                    platform=Platform.TIKTOK,
                    anchor_name="Example Anchor",
                    title="TikTok Demo Stream",
                    status=TaskStatus.IDLE,
                ),
                RecordTask(
                    task_id="task-003",
                    url="https://live.kuaishou.com/u/example",
                    platform=Platform.KUAISHOU,
                    anchor_name="Demo Anchor B",
                    title="Replay Monitor",
                    status=TaskStatus.FAILED,
                    last_error="Cookie expired. Please sign in again.",
                ),
            ]
        )

    def visible_tasks(self, keyword: str = "") -> list[RecordTask]:
        normalized = keyword.strip().lower()
        if not normalized:
            return list(self.tasks)

        return [
            task
            for task in self.tasks
            if normalized in task.task_id.lower()
            or normalized in task.url.lower()
            or normalized in task.platform.value.lower()
            or any(normalized in term for term in PLATFORM_SEARCH_TERMS.get(task.platform, ()))
            or normalized in (task.anchor_name or "").lower()
            or normalized in (task.display_name or "").lower()
            or normalized in (task.title or "").lower()
            or normalized in task.status.value.lower()
            or any(normalized in term for term in STATUS_SEARCH_TERMS.get(task.status, ()))
        ]

    def running_tasks(self) -> list[RecordTask]:
        return [task for task in self.tasks if task.status == TaskStatus.RUNNING]

    def get_task(self, task_id: str) -> RecordTask | None:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def add_task(self, task: RecordTask) -> None:
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> RecordTask | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        self.tasks.remove(task)
        return task

    def summary_text(self, visible_tasks: list[RecordTask]) -> str:
        enabled = sum(1 for task in self.tasks if task.enabled)
        running = len(self.running_tasks())
        return f"共 {len(self.tasks)} 个任务，当前显示 {len(visible_tasks)} 个，启用 {enabled} 个，运行中 {running} 个"

    def is_task_active(self, task: RecordTask, record_manager: RecordManager | None = None) -> bool:
        managed_task = task
        if record_manager is not None:
            managed_task = record_manager.get_task(task.task_id) or task
        return managed_task.status in {TaskStatus.PENDING, TaskStatus.RUNNING}

    def default_quality(self, record_manager: RecordManager | None = None) -> str:
        if record_manager is not None and record_manager.config is not None:
            return record_manager.config.quality
        return "原画"

    def save_task(
        self,
        payload: dict[str, str | bool],
        *,
        task_persistence: TaskPersistenceService | None,
        record_manager: RecordManager | None = None,
        task_id: str | None = None,
    ) -> TaskActionResult:
        if task_persistence is None:
            return TaskActionResult(
                ok=False,
                message="当前未配置任务存储，无法保存任务。",
                level=LEVEL_WARNING,
                status_message="当前未配置任务存储，无法保存任务。",
            )

        try:
            if task_id is None:
                new_task = task_persistence.create_task(tasks=self.tasks, **payload)
                self.add_task(new_task)
                if record_manager is not None:
                    record_manager.add_task(new_task)
                self._persist_tasks(task_persistence)
                return TaskActionResult(
                    ok=True,
                    message=f"已新增任务 {new_task.task_id}。",
                    status_message=f"已新增任务 {new_task.task_id}",
                    refresh=True,
                    selected_task_id=new_task.task_id,
                )

            task = self.get_task(task_id)
            if task is None:
                return TaskActionResult(
                    ok=False,
                    message=f"未找到任务 {task_id}。",
                    level=LEVEL_WARNING,
                    status_message=f"未找到任务 {task_id}。",
                )

            task_persistence.update_task(task, **payload)
            self._persist_tasks(task_persistence)
            return TaskActionResult(
                ok=True,
                message=f"已更新任务 {task.task_id}。",
                status_message=f"已保存任务 {task.task_id}",
                refresh=True,
                selected_task_id=task.task_id,
            )
        except Exception as exc:
            return TaskActionResult(
                ok=False,
                message=f"任务保存失败: {exc}",
                level=LEVEL_ERROR,
                status_message="任务保存失败。",
                dialog_title="保存失败",
                dialog_message=f"任务保存失败：{exc}",
            )

    def import_tasks(
        self,
        file_path: Path,
        *,
        task_persistence: TaskPersistenceService | None,
        record_manager: RecordManager | None = None,
        default_quality: str = "原画",
    ) -> TaskActionResult:
        if task_persistence is None:
            return TaskActionResult(
                ok=False,
                message="当前未配置任务存储，无法导入任务。",
                level=LEVEL_WARNING,
                status_message="当前未配置任务存储，无法导入任务。",
            )

        try:
            imported_tasks = task_persistence.load_tasks_from_file(Path(file_path), default_quality=default_quality)
            if not imported_tasks:
                return TaskActionResult(
                    ok=False,
                    message=f"从 {Path(file_path).name} 未解析到可导入的任务。",
                    level=LEVEL_WARNING,
                    status_message="未发现可导入的任务。",
                )

            active_task_ids = {task.task_id for task in self.tasks if self.is_task_active(task, record_manager)}
            merged_tasks, added, updated, skipped = task_persistence.merge_imported_tasks(
                self.tasks,
                imported_tasks,
                active_task_ids=active_task_ids,
            )
            self.tasks = merged_tasks
            self._sync_record_manager_tasks(record_manager)
            self._persist_tasks(task_persistence)
            summary = f"已导入 {added} 个新任务，更新 {updated} 个，跳过 {skipped} 个。"
            return TaskActionResult(
                ok=True,
                message=f"从 {Path(file_path).name} 导入任务完成：{summary}",
                status_message=summary,
                status_timeout=4000,
                refresh=True,
            )
        except Exception as exc:
            return TaskActionResult(
                ok=False,
                message=f"任务导入失败: {exc}",
                level=LEVEL_ERROR,
                status_message="任务导入失败。",
                dialog_title="导入失败",
                dialog_message=f"任务导入失败：{exc}",
            )

    def export_tasks(self, file_path: Path, *, task_persistence: TaskPersistenceService | None) -> TaskActionResult:
        if task_persistence is None:
            return TaskActionResult(
                ok=False,
                message="当前未配置任务存储，无法导出任务。",
                level=LEVEL_WARNING,
                status_message="当前未配置任务存储，无法导出任务。",
            )
        if not self.tasks:
            return TaskActionResult(
                ok=False,
                message="当前没有可导出的任务。",
                level=LEVEL_WARNING,
                status_message="当前没有可导出的任务。",
            )

        try:
            task_persistence.export_tasks_to_file(self.tasks, Path(file_path))
            return TaskActionResult(
                ok=True,
                message=f"已导出 {len(self.tasks)} 个任务到 {Path(file_path)}。",
                status_message=f"任务已导出到 {Path(file_path).name}",
            )
        except Exception as exc:
            return TaskActionResult(
                ok=False,
                message=f"任务导出失败: {exc}",
                level=LEVEL_ERROR,
                status_message="任务导出失败。",
                dialog_title="导出失败",
                dialog_message=f"任务导出失败：{exc}",
            )

    def delete_task(
        self,
        task_id: str,
        *,
        task_persistence: TaskPersistenceService | None,
        record_manager: RecordManager | None = None,
    ) -> TaskActionResult:
        task = self.get_task(task_id)
        if task is None:
            return TaskActionResult(
                ok=False,
                message=f"未找到任务 {task_id}。",
                level=LEVEL_WARNING,
                status_message=f"未找到任务 {task_id}。",
            )

        try:
            if record_manager is not None:
                record_manager.remove_task(task.task_id)
            self.remove_task(task.task_id)
            self._persist_tasks(task_persistence)
            return TaskActionResult(
                ok=True,
                message=f"已删除任务 {task.task_id}。",
                status_message=f"已删除 {task.task_id}",
                refresh=True,
            )
        except Exception as exc:
            return TaskActionResult(
                ok=False,
                message=f"删除 {task.task_id} 失败: {exc}",
                level=LEVEL_ERROR,
                status_message="任务删除失败。",
                dialog_title="删除失败",
                dialog_message=f"任务删除失败：{exc}",
            )

    def start_task(self, task_id: str, *, record_manager: RecordManager | None = None) -> TaskActionResult:
        task = self.get_task(task_id)
        if task is None:
            return TaskActionResult(
                ok=False,
                message=f"未找到任务 {task_id}。",
                level=LEVEL_WARNING,
                status_message=f"未找到任务 {task_id}。",
            )
        if self.is_task_active(task, record_manager):
            return TaskActionResult(
                ok=False,
                message=f"{task.task_id} 已在运行中。",
                level=LEVEL_WARNING,
                status_message=f"{task.task_id} 已在运行中。",
                status_timeout=2500,
            )
        if record_manager is None:
            return TaskActionResult(
                ok=False,
                message=f"请求启动 {task.task_id}，但当前没有连接录制管理器。",
                level=LEVEL_WARNING,
            )

        try:
            record_manager.start_task(task.task_id)
            return TaskActionResult(
                ok=True,
                message=f"已启动任务 {task.task_id}。",
                status_message=f"已启动 {task.task_id}",
                refresh=True,
                selected_task_id=task.task_id,
            )
        except Exception as exc:
            task.last_error = str(exc)
            return TaskActionResult(
                ok=False,
                message=f"启动 {task.task_id} 失败: {exc}",
                level=LEVEL_ERROR,
                status_message=f"{task.task_id} 启动失败",
                status_timeout=4000,
                refresh=True,
                selected_task_id=task.task_id,
            )

    def stop_task(self, task_id: str, *, record_manager: RecordManager | None = None) -> TaskActionResult:
        task = self.get_task(task_id)
        if task is None:
            return TaskActionResult(
                ok=False,
                message=f"未找到任务 {task_id}。",
                level=LEVEL_WARNING,
                status_message=f"未找到任务 {task_id}。",
            )
        if not self.is_task_active(task, record_manager):
            return TaskActionResult(
                ok=False,
                message=f"{task.task_id} 当前未在运行。",
                level=LEVEL_WARNING,
                status_message=f"{task.task_id} 当前未在运行。",
                status_timeout=2500,
            )
        if record_manager is None:
            return TaskActionResult(
                ok=False,
                message=f"请求停止 {task.task_id}，但当前没有连接录制管理器。",
                level=LEVEL_WARNING,
            )

        try:
            record_manager.stop_task(task.task_id)
            return TaskActionResult(
                ok=True,
                message=f"已停止任务 {task.task_id}。",
                status_message=f"已停止 {task.task_id}",
                refresh=True,
                selected_task_id=task.task_id,
            )
        except Exception as exc:
            task.last_error = str(exc)
            return TaskActionResult(
                ok=False,
                message=f"停止 {task.task_id} 失败: {exc}",
                level=LEVEL_ERROR,
                status_message=f"{task.task_id} 停止失败",
                status_timeout=4000,
                refresh=True,
                selected_task_id=task.task_id,
            )

    def _persist_tasks(self, task_persistence: TaskPersistenceService | None) -> None:
        if task_persistence is None:
            return
        task_persistence.save_tasks(self.tasks)

    def _sync_record_manager_tasks(self, record_manager: RecordManager | None) -> None:
        if record_manager is None:
            return
        for task in self.tasks:
            if record_manager.get_task(task.task_id) is None:
                record_manager.add_task(task)
