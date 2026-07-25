from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from client.core.enums import Platform, TaskStatus
from client.core.models import AppConfig, RecordTask
from client.core.task_persistence import TaskPersistenceService
from client.viewmodels.task_viewmodel import TaskViewModel


class _FakeRecordManager:
    def __init__(self, tasks: list[RecordTask] | None = None, quality: str = "原画") -> None:
        self.tasks = {task.task_id: task for task in (tasks or [])}
        self.config = AppConfig(quality=quality)
        self.start_calls: list[str] = []
        self.stop_calls: list[str] = []
        self.remove_calls: list[str] = []
        self._start_errors: dict[str, Exception] = {}
        self._stop_errors: dict[str, Exception] = {}

    def add_task(self, task: RecordTask) -> None:
        self.tasks[task.task_id] = task

    def get_task(self, task_id: str) -> RecordTask | None:
        return self.tasks.get(task_id)

    def remove_task(self, task_id: str) -> None:
        self.remove_calls.append(task_id)
        self.tasks.pop(task_id, None)

    def start_task(self, task_id: str) -> None:
        self.start_calls.append(task_id)
        exc = self._start_errors.get(task_id)
        if exc is not None:
            raise exc
        task = self.tasks[task_id]
        task.status = TaskStatus.RUNNING

    def stop_task(self, task_id: str) -> None:
        self.stop_calls.append(task_id)
        exc = self._stop_errors.get(task_id)
        if exc is not None:
            raise exc
        task = self.tasks[task_id]
        task.status = TaskStatus.STOPPED


class TaskViewModelTests(unittest.TestCase):
    def make_workspace(self, prefix: str) -> Path:
        root = Path.cwd() / f"{prefix}_{uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def test_save_task_creates_and_persists_task(self) -> None:
        root = self.make_workspace("tmp_task_viewmodel_create")
        store_path = root / "client_data" / "tasks.json"
        persistence = TaskPersistenceService(store_path)
        viewmodel = TaskViewModel()
        record_manager = _FakeRecordManager()

        result = viewmodel.save_task(
            {
                "url": "live.douyin.com/123",
                "quality": "超清",
                "display_name": "主播甲",
                "enabled": True,
            },
            task_persistence=persistence,
            record_manager=record_manager,
        )

        self.assertTrue(result.ok)
        self.assertEqual(1, len(viewmodel.tasks))
        self.assertEqual("task-001", viewmodel.tasks[0].task_id)
        self.assertIn("task-001", record_manager.tasks)
        payload = json.loads(store_path.read_text(encoding="utf-8"))
        self.assertEqual(1, len(payload["tasks"]))

    def test_import_tasks_updates_existing_and_syncs_record_manager(self) -> None:
        root = self.make_workspace("tmp_task_viewmodel_import")
        store_path = root / "client_data" / "tasks.json"
        import_path = root / "URL_config.ini"
        import_path.write_text(
            "\n".join(
                [
                    "超清,live.douyin.com/123,更新主播",
                    "高清,https://www.tiktok.com/@demo/live,新增主播",
                ]
            ),
            encoding="utf-8-sig",
        )
        existing = RecordTask(
            task_id="task-001",
            url="https://live.douyin.com/123",
            platform=Platform.DOUYIN,
            quality="原画",
            enabled=True,
            display_name="旧主播",
        )
        persistence = TaskPersistenceService(store_path)
        viewmodel = TaskViewModel(tasks=[existing])
        record_manager = _FakeRecordManager(tasks=[existing], quality="蓝光")

        result = viewmodel.import_tasks(
            import_path,
            task_persistence=persistence,
            record_manager=record_manager,
            default_quality=viewmodel.default_quality(record_manager),
        )

        self.assertTrue(result.ok)
        self.assertEqual(2, len(viewmodel.tasks))
        self.assertEqual("超清", existing.quality)
        self.assertEqual("更新主播", existing.display_name)
        self.assertIn("task-002", record_manager.tasks)

    def test_delete_task_removes_task_and_persists(self) -> None:
        root = self.make_workspace("tmp_task_viewmodel_delete")
        store_path = root / "client_data" / "tasks.json"
        store_path.parent.mkdir(parents=True, exist_ok=True)
        task = RecordTask(
            task_id="task-001",
            url="https://live.douyin.com/123",
            platform=Platform.DOUYIN,
        )
        persistence = TaskPersistenceService(store_path)
        persistence.save_tasks([task])
        viewmodel = TaskViewModel(tasks=[task])
        record_manager = _FakeRecordManager(tasks=[task])

        result = viewmodel.delete_task(
            "task-001",
            task_persistence=persistence,
            record_manager=record_manager,
        )

        self.assertTrue(result.ok)
        self.assertEqual([], viewmodel.tasks)
        self.assertEqual(["task-001"], record_manager.remove_calls)
        payload = json.loads(store_path.read_text(encoding="utf-8"))
        self.assertEqual([], payload["tasks"])

    def test_start_task_failure_updates_error_message(self) -> None:
        task = RecordTask(
            task_id="task-001",
            url="https://live.douyin.com/123",
            platform=Platform.DOUYIN,
        )
        viewmodel = TaskViewModel(tasks=[task])
        record_manager = _FakeRecordManager(tasks=[task])
        record_manager._start_errors["task-001"] = RuntimeError("network boom")

        result = viewmodel.start_task("task-001", record_manager=record_manager)

        self.assertFalse(result.ok)
        self.assertEqual("network boom", task.last_error)
        self.assertIn("失败", result.status_message or "")

    def test_visible_tasks_filters_and_summary_text_matches(self) -> None:
        tasks = [
            RecordTask(task_id="task-001", url="https://live.douyin.com/123", platform=Platform.DOUYIN, enabled=True),
            RecordTask(
                task_id="task-002",
                url="https://www.tiktok.com/@demo/live",
                platform=Platform.TIKTOK,
                enabled=False,
                status=TaskStatus.RUNNING,
                display_name="主播乙",
            ),
        ]
        viewmodel = TaskViewModel(tasks=tasks)

        visible = viewmodel.visible_tasks("主播乙")
        visible_by_platform = viewmodel.visible_tasks("抖音")
        visible_by_status = viewmodel.visible_tasks("运行中")

        self.assertEqual([tasks[1]], visible)
        self.assertEqual([tasks[0]], visible_by_platform)
        self.assertEqual([tasks[1]], visible_by_status)
        self.assertEqual("共 2 个任务，当前显示 1 个，启用 1 个，运行中 1 个", viewmodel.summary_text(visible))


if __name__ == "__main__":
    unittest.main()
