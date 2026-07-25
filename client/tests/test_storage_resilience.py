from __future__ import annotations

import json
import shutil
import unittest
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from client.core.config_service import ConfigService
from client.core.enums import Platform, TaskStatus
from client.core.history_service import HistoryService
from client.core.models import RecordSession, RecordTask
from client.core.task_persistence import TaskPersistenceService


class StorageResilienceTests(unittest.TestCase):
    def make_workspace(self, prefix: str) -> Path:
        root = Path.cwd() / f"{prefix}_{uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def test_config_service_load_local_returns_none_for_invalid_json_and_keeps_backup(self) -> None:
        root = self.make_workspace("tmp_config_resilience")
        local_config_path = root / "client_data" / "config.json"
        local_config_path.parent.mkdir(parents=True, exist_ok=True)
        local_config_path.write_text("{ invalid json", encoding="utf-8")

        service = ConfigService(root_dir=root, local_config_path=local_config_path)

        config = service.load_local()

        self.assertIsNone(config)
        self.assertFalse(local_config_path.exists())
        self.assertEqual(1, len(list(local_config_path.parent.glob("config.broken-*.json"))))

    def test_task_persistence_recovers_from_invalid_json_using_seed_tasks(self) -> None:
        root = self.make_workspace("tmp_task_store_resilience")
        tasks_path = root / "client_data" / "tasks.json"
        tasks_path.parent.mkdir(parents=True, exist_ok=True)
        tasks_path.write_text("{ invalid json", encoding="utf-8")
        seed_task = RecordTask(
            task_id="task-001",
            url="https://live.douyin.com/123",
            platform=Platform.DOUYIN,
            quality="原画",
            enabled=True,
            display_name="主播A",
        )
        service = TaskPersistenceService(tasks_path)

        tasks = service.load_tasks(seed_tasks=[seed_task])

        self.assertEqual(1, len(tasks))
        self.assertEqual("task-001", tasks[0].task_id)
        self.assertEqual("https://live.douyin.com/123", tasks[0].url)
        payload = json.loads(tasks_path.read_text(encoding="utf-8"))
        self.assertEqual(1, len(payload["tasks"]))
        self.assertEqual(1, len(list(tasks_path.parent.glob("tasks.broken-*.json"))))

    def test_history_service_skips_invalid_record_and_keeps_valid_records(self) -> None:
        root = self.make_workspace("tmp_history_resilience")
        history_path = root / "client_data" / "history.json"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "records": [
                        {
                            "task_id": "task-001",
                            "status": "completed",
                            "platform": "douyin",
                            "display_name": "主播A",
                            "title": "已完成",
                            "file_path": str(root / "downloads" / "a.ts"),
                            "started_at": "2026-03-30T12:00:00",
                            "finished_at": "2026-03-30T12:30:00",
                            "error_message": "",
                        },
                        {
                            "task_id": "task-002",
                            "status": "running",
                            "platform": "douyin",
                            "display_name": "主播B",
                            "title": "损坏记录",
                            "file_path": str(root / "downloads" / "b.ts"),
                            "started_at": "not-a-date",
                            "finished_at": None,
                            "error_message": "",
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        service = HistoryService(history_path)

        self.assertEqual(1, len(service.records))
        self.assertEqual("task-001", service.records[0].task_id)
        self.assertEqual(TaskStatus.COMPLETED, service.records[0].status)

    def test_history_service_records_can_still_be_updated_after_partial_load(self) -> None:
        root = self.make_workspace("tmp_history_update")
        history_path = root / "client_data" / "history.json"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text(
            json.dumps({"version": 1, "records": [{"task_id": "bad", "started_at": "oops"}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        service = HistoryService(history_path)
        task = RecordTask(
            task_id="task-003",
            url="https://live.douyin.com/456",
            platform=Platform.DOUYIN,
            display_name="主播C",
        )
        session = RecordSession(
            task_id="task-003",
            started_at=datetime(2026, 3, 31, 12, 0, 0),
            output_file=root / "downloads" / "c.ts",
        )

        service.record_started(task, session)
        service.record_finished(task, TaskStatus.STOPPED)

        saved_payload = json.loads(history_path.read_text(encoding="utf-8"))
        self.assertEqual(1, len(saved_payload["records"]))
        self.assertEqual("task-003", saved_payload["records"][0]["task_id"])


if __name__ == "__main__":
    unittest.main()
