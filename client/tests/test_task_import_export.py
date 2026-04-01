from __future__ import annotations

import json
import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from client.core.enums import Platform, TaskStatus
from client.core.models import AppConfig, RecordTask
from client.core.task_persistence import TaskPersistenceService
from client.ui.pages.tasks_page import TasksPage
from client.viewmodels.task_viewmodel import TaskViewModel


class _FakeRecordManager:
    def __init__(self, tasks: list[RecordTask] | None = None, quality: str = "原画") -> None:
        self.tasks = {task.task_id: task for task in (tasks or [])}
        self.config = AppConfig(quality=quality)

    def add_task(self, task: RecordTask) -> None:
        self.tasks[task.task_id] = task

    def get_task(self, task_id: str) -> RecordTask | None:
        return self.tasks.get(task_id)

    def sync_task_states(self) -> bool:
        return False


class TaskImportExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def make_workspace(self, prefix: str) -> Path:
        root = Path.cwd() / f"{prefix}_{uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def test_load_tasks_from_legacy_file_parses_enabled_disabled_and_name(self) -> None:
        root = self.make_workspace("tmp_task_import_legacy")
        import_path = root / "URL_config.ini"
        import_path.write_text(
            "\n".join(
                [
                    "原画,live.douyin.com/123,主播甲",
                    "#超清,https://www.showroom-live.com/r/demo,主播乙",
                    "www.tiktok.com/@demo/live,主播丙",
                ]
            ),
            encoding="utf-8-sig",
        )
        service = TaskPersistenceService(root / "client_data" / "tasks.json")

        tasks = service.load_tasks_from_file(import_path, default_quality="蓝光")

        self.assertEqual(3, len(tasks))
        self.assertEqual("https://live.douyin.com/123", tasks[0].url)
        self.assertTrue(tasks[0].enabled)
        self.assertEqual("原画", tasks[0].quality)
        self.assertEqual("主播甲", tasks[0].display_name)
        self.assertFalse(tasks[1].enabled)
        self.assertEqual("超清", tasks[1].quality)
        self.assertEqual(Platform.SHOWROOM, tasks[1].platform)
        self.assertEqual("蓝光", tasks[2].quality)
        self.assertEqual("主播丙", tasks[2].display_name)

    def test_load_tasks_from_json_supports_raw_list(self) -> None:
        root = self.make_workspace("tmp_task_import_json")
        import_path = root / "tasks-import.json"
        import_path.write_text(
            json.dumps(
                [
                    {
                        "task_id": "legacy-1",
                        "url": "live.kuaishou.com/u/demo",
                        "platform": "kuaishou",
                        "quality": "高清",
                        "enabled": True,
                        "display_name": "主播快手",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        service = TaskPersistenceService(root / "client_data" / "tasks.json")

        tasks = service.load_tasks_from_file(import_path)

        self.assertEqual(1, len(tasks))
        self.assertEqual("https://live.kuaishou.com/u/demo", tasks[0].url)
        self.assertEqual(Platform.KUAISHOU, tasks[0].platform)
        self.assertEqual("高清", tasks[0].quality)

    def test_merge_imported_tasks_updates_existing_and_skips_active_duplicates(self) -> None:
        root = self.make_workspace("tmp_task_import_merge")
        service = TaskPersistenceService(root / "client_data" / "tasks.json")
        existing_idle = RecordTask(
            task_id="task-001",
            url="https://live.douyin.com/123",
            platform=Platform.DOUYIN,
            quality="原画",
            enabled=True,
            display_name="旧名称",
        )
        existing_active = RecordTask(
            task_id="task-002",
            url="https://www.showroom-live.com/r/demo",
            platform=Platform.SHOWROOM,
            quality="标清",
            enabled=True,
            display_name="运行中任务",
            status=TaskStatus.RUNNING,
        )
        imported = [
            RecordTask(
                task_id="import-1",
                url="live.douyin.com/123",
                quality="超清",
                enabled=False,
                display_name="新名称",
            ),
            RecordTask(
                task_id="import-2",
                url="https://www.showroom-live.com/r/demo",
                quality="蓝光",
                enabled=False,
                display_name="不该覆盖",
            ),
            RecordTask(
                task_id="import-3",
                url="https://www.tiktok.com/@demo/live",
                quality="高清",
                enabled=True,
                display_name="新增任务",
            ),
        ]

        merged, added, updated, skipped = service.merge_imported_tasks(
            [existing_idle, existing_active],
            imported,
            active_task_ids={"task-002"},
        )

        self.assertEqual(3, len(merged))
        self.assertEqual(1, added)
        self.assertEqual(1, updated)
        self.assertEqual(1, skipped)
        self.assertEqual("task-001", existing_idle.task_id)
        self.assertEqual("超清", existing_idle.quality)
        self.assertFalse(existing_idle.enabled)
        self.assertEqual("新名称", existing_idle.display_name)
        self.assertEqual("标清", existing_active.quality)
        self.assertEqual("task-003", merged[-1].task_id)
        self.assertEqual(Platform.TIKTOK, merged[-1].platform)

    def test_export_tasks_to_json_writes_payload(self) -> None:
        root = self.make_workspace("tmp_task_export_json")
        export_path = root / "tasks-export.json"
        service = TaskPersistenceService(root / "client_data" / "tasks.json")
        tasks = [
            RecordTask(
                task_id="task-001",
                url="https://live.douyin.com/123",
                platform=Platform.DOUYIN,
                quality="原画",
                enabled=True,
                display_name="主播甲",
            )
        ]

        service.export_tasks_to_file(tasks, export_path)

        payload = json.loads(export_path.read_text(encoding="utf-8"))
        self.assertEqual(1, payload["version"])
        self.assertEqual(1, len(payload["tasks"]))
        self.assertEqual("task-001", payload["tasks"][0]["task_id"])
        self.assertEqual("主播甲", payload["tasks"][0]["display_name"])

    def test_export_tasks_to_legacy_text_writes_legacy_lines(self) -> None:
        root = self.make_workspace("tmp_task_export_legacy")
        export_path = root / "URL_config.ini"
        service = TaskPersistenceService(root / "client_data" / "tasks.json")
        tasks = [
            RecordTask(
                task_id="task-001",
                url="https://live.douyin.com/123",
                platform=Platform.DOUYIN,
                quality="原画",
                enabled=True,
                display_name="主播甲",
            ),
            RecordTask(
                task_id="task-002",
                url="https://www.showroom-live.com/r/demo",
                platform=Platform.SHOWROOM,
                quality="蓝光",
                enabled=False,
                display_name="主播乙",
            ),
        ]

        service.export_tasks_to_file(tasks, export_path)

        content = export_path.read_text(encoding="utf-8-sig")
        self.assertIn("原画,https://live.douyin.com/123,主播甲", content)
        self.assertIn("#蓝光,https://www.showroom-live.com/r/demo,主播乙", content)

    def test_tasks_page_import_merges_and_persists_tasks(self) -> None:
        root = self.make_workspace("tmp_tasks_page_import")
        store_path = root / "client_data" / "tasks.json"
        store_path.parent.mkdir(parents=True, exist_ok=True)
        import_path = root / "tasks-import.json"
        import_path.write_text(
            json.dumps(
                {
                    "tasks": [
                        {
                            "task_id": "import-1",
                            "url": "https://live.douyin.com/123",
                            "platform": "douyin",
                            "quality": "超清",
                            "enabled": False,
                            "display_name": "更新主播",
                        },
                        {
                            "task_id": "import-2",
                            "url": "https://www.tiktok.com/@demo/live",
                            "platform": "tiktok",
                            "quality": "高清",
                            "enabled": True,
                            "display_name": "新增主播",
                        },
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        existing_task = RecordTask(
            task_id="task-001",
            url="https://live.douyin.com/123",
            platform=Platform.DOUYIN,
            quality="原画",
            enabled=True,
            display_name="旧主播",
        )
        task_persistence = TaskPersistenceService(store_path)
        record_manager = _FakeRecordManager(tasks=[existing_task], quality="蓝光")
        page = TasksPage(
            viewmodel=TaskViewModel(tasks=[existing_task]),
            record_manager=record_manager,
            task_persistence=task_persistence,
        )
        self.addCleanup(page.close)
        self.addCleanup(page._status_timer.stop)

        with patch("client.ui.pages.tasks_page.QFileDialog.getOpenFileName", return_value=(str(import_path), "JSON 文件 (*.json)")):
            page._import_tasks()

        self.assertEqual(2, len(page.viewmodel.tasks))
        self.assertEqual("超清", existing_task.quality)
        self.assertFalse(existing_task.enabled)
        self.assertEqual("更新主播", existing_task.display_name)
        self.assertIn("task-002", record_manager.tasks)
        payload = json.loads(store_path.read_text(encoding="utf-8"))
        self.assertEqual(2, len(payload["tasks"]))

    def test_tasks_page_export_writes_selected_file(self) -> None:
        root = self.make_workspace("tmp_tasks_page_export")
        store_path = root / "client_data" / "tasks.json"
        export_path = root / "tasks-export.ini"
        task = RecordTask(
            task_id="task-001",
            url="https://live.douyin.com/123",
            platform=Platform.DOUYIN,
            quality="原画",
            enabled=True,
            display_name="主播甲",
        )
        page = TasksPage(
            viewmodel=TaskViewModel(tasks=[task]),
            record_manager=_FakeRecordManager(tasks=[task]),
            task_persistence=TaskPersistenceService(store_path),
        )
        self.addCleanup(page.close)
        self.addCleanup(page._status_timer.stop)

        with patch("client.ui.pages.tasks_page.QFileDialog.getSaveFileName", return_value=(str(export_path), "旧版配置 (*.ini)")):
            page._export_tasks()

        content = export_path.read_text(encoding="utf-8-sig")
        self.assertIn("原画,https://live.douyin.com/123,主播甲", content)


if __name__ == "__main__":
    unittest.main()
