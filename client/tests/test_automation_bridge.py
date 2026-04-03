from __future__ import annotations

import json
import os
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from client.app_settings import AppSettings
from client.core.enums import TaskStatus
from client.core.history_service import HistoryService
from client.core.models import AppConfig, RecordTask
from client.core.platform_router import PlatformRouter
from client.core.task_persistence import TaskPersistenceService
from client.infra.process.automation_bridge import AutomationBridge
from client.ui.main_window import MainWindow
from client.viewmodels.settings_viewmodel import SettingsViewModel
from client.viewmodels.task_viewmodel import TaskViewModel


class _FakeRecordManager:
    def __init__(self, tasks: list[RecordTask]) -> None:
        self.tasks = {task.task_id: task for task in tasks}
        self.config = AppConfig()
        self.log_handler = None

    def set_log_handler(self, handler) -> None:
        self.log_handler = handler

    def add_task(self, task: RecordTask) -> None:
        self.tasks[task.task_id] = task

    def remove_task(self, task_id: str) -> None:
        self.tasks.pop(task_id, None)

    def get_task(self, task_id: str) -> RecordTask | None:
        return self.tasks.get(task_id)

    def start_task(self, task_id: str) -> None:
        self.tasks[task_id].status = TaskStatus.RUNNING

    def stop_task(self, task_id: str) -> None:
        self.tasks[task_id].status = TaskStatus.STOPPED

    def sync_task_states(self) -> bool:
        return False


class _FakeController:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def handle_automation_command(self, command: str, payload: dict | None = None) -> dict:
        request = payload or {}
        self.calls.append((command, request))
        return {"command": command, "payload": request}


class AutomationBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def make_workspace(self, prefix: str) -> Path:
        root = Path.cwd() / f"{prefix}_{uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def create_window(self, root: Path) -> MainWindow:
        tasks_path = root / "client_data" / "tasks.json"
        history_path = root / "client_data" / "history.json"
        task_persistence = TaskPersistenceService(tasks_path, platform_router=PlatformRouter())
        history_service = HistoryService(history_path)
        record_manager = _FakeRecordManager([])
        window = MainWindow(
            settings=AppSettings(data_dir=root / "client_data"),
            task_viewmodel=TaskViewModel(tasks=[]),
            settings_viewmodel=SettingsViewModel(config=AppConfig(close_to_tray=False, minimize_to_tray=False)),
            record_manager=record_manager,
            task_persistence=task_persistence,
            history_service=history_service,
        )
        window.tasks_page._status_timer.stop()
        window._scheduler_timer.stop()
        window._runtime_timer.stop()
        self.addCleanup(window.deleteLater)
        return window

    def test_bridge_poll_once_writes_response(self) -> None:
        root = self.make_workspace("tmp_automation_bridge")
        controller = _FakeController()
        bridge = AutomationBridge(root / "automation", handler=controller)
        bridge.paths.request_path.write_text(
            json.dumps({"id": "req-1", "command": "ping", "payload": {"value": 1}}, ensure_ascii=False),
            encoding="utf-8",
        )

        processed = bridge.poll_once()

        self.assertTrue(processed)
        response = json.loads(bridge.paths.response_path.read_text(encoding="utf-8"))
        self.assertTrue(response["ok"])
        self.assertEqual("req-1", response["request_id"])
        self.assertEqual("ping", response["data"]["command"])
        self.assertEqual({"value": 1}, response["data"]["payload"])

    def test_main_window_automation_add_start_stop_task(self) -> None:
        root = self.make_workspace("tmp_automation_window")
        window = self.create_window(root)

        add_response = window.handle_automation_command(
            "add_task",
            {
                "url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
                "display_name": "Automation_Test",
                "quality": "原画",
                "enabled": True,
            },
        )
        self.assertTrue(add_response["result"]["ok"])
        task_id = add_response["task"]["task_id"]
        self.assertEqual(1, len(window.tasks_page.viewmodel.tasks))

        start_response = window.handle_automation_command("start_task", {"task_id": task_id})
        self.assertTrue(start_response["result"]["ok"])
        self.assertEqual("running", start_response["task"]["status"])

        stop_response = window.handle_automation_command("stop_task", {"task_id": task_id})
        self.assertTrue(stop_response["result"]["ok"])
        self.assertEqual("stopped", stop_response["task"]["status"])

        list_response = window.handle_automation_command("list_tasks")
        self.assertEqual(1, len(list_response["tasks"]))
        self.assertEqual(task_id, list_response["tasks"][0]["task_id"])

    def test_main_window_automation_edit_delete_import_export_logs_and_tabs(self) -> None:
        root = self.make_workspace("tmp_automation_window_ops")
        window = self.create_window(root)

        add_response = window.handle_automation_command(
            "add_task",
            {
                "url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
                "display_name": "Automation_Edit",
                "quality": "鍘熺敾",
                "enabled": True,
            },
        )
        task_id = add_response["task"]["task_id"]

        edit_response = window.handle_automation_command(
            "edit_task",
            {
                "task_id": task_id,
                "display_name": "Automation_Edited",
                "enabled": False,
            },
        )
        self.assertTrue(edit_response["result"]["ok"])
        self.assertEqual("Automation_Edited", edit_response["task"]["display_name"])
        self.assertFalse(edit_response["task"]["enabled"])

        export_path = root / "exported_tasks.json"
        export_response = window.handle_automation_command("export_tasks", {"file_path": str(export_path)})
        self.assertTrue(export_response["result"]["ok"])
        self.assertTrue(export_path.exists())

        delete_response = window.handle_automation_command("delete_task", {"task_id": task_id})
        self.assertTrue(delete_response["result"]["ok"])
        self.assertEqual(0, len(window.tasks_page.viewmodel.tasks))

        import_response = window.handle_automation_command("import_tasks", {"file_path": str(export_path)})
        self.assertTrue(import_response["result"]["ok"])
        self.assertEqual(1, len(import_response["tasks"]))

        tabs_response = window.handle_automation_command("list_tabs")
        self.assertIn("logs", tabs_response["tabs"])

        set_tab_response = window.handle_automation_command("set_current_tab", {"tab": "logs"})
        self.assertEqual("logs", set_tab_response["current_tab"])

        logs_response = window.handle_automation_command("get_logs", {"keyword": "自动化"})
        self.assertGreaterEqual(logs_response["count"], 1)

        clear_logs_response = window.handle_automation_command("clear_logs")
        self.assertTrue(clear_logs_response["cleared"])
        self.assertEqual(0, window.handle_automation_command("get_logs")["count"])


if __name__ == "__main__":
    unittest.main()
