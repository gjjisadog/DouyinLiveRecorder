from __future__ import annotations

import json
import os
import shutil
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from client.app_settings import AppSettings
from client.core.enums import TaskStatus
from client.core.history_service import HistoryService
from client.core.models import AppConfig, RecordTask
from client.core.platform_router import PlatformRouter
from client.core.task_persistence import TaskPersistenceService
from client.infra.process.automation_bridge import AutomationBridge, write_json_atomically
from client.ui.main_window import MainWindow
from client.viewmodels.settings_viewmodel import SettingsViewModel
from client.viewmodels.task_viewmodel import TaskViewModel
from scripts.exe_automation_acceptance import send_command


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

    def test_write_json_atomically_replaces_file_without_temp_leftovers(self) -> None:
        root = self.make_workspace("tmp_automation_bridge_atomic")
        response_path = root / "automation" / "response.json"
        response_path.parent.mkdir(parents=True, exist_ok=True)
        response_path.write_text('{"stale": true}', encoding="utf-8")

        write_json_atomically(response_path, {"ok": True, "request_id": "req-2"})

        self.assertEqual({"ok": True, "request_id": "req-2"}, json.loads(response_path.read_text(encoding="utf-8")))
        self.assertEqual([], list(response_path.parent.glob("response.json.*.tmp")))

    def test_send_command_retries_when_response_json_is_temporarily_invalid(self) -> None:
        root = self.make_workspace("tmp_automation_send_command")
        automation_dir = root / "automation"
        automation_dir.mkdir(parents=True, exist_ok=True)
        response_path = automation_dir / "response.json"
        request_path = automation_dir / "request.json"

        def write_transient_response() -> None:
            deadline = time.time() + 5
            while time.time() < deadline:
                if request_path.exists():
                    request = json.loads(request_path.read_text(encoding="utf-8"))
                    response_path.write_text("", encoding="utf-8")
                    time.sleep(0.1)
                    write_json_atomically(
                        response_path,
                        {
                            "ok": True,
                            "request_id": request["id"],
                            "command": request["command"],
                            "data": {"echo": request["payload"]},
                        },
                    )
                    return
                time.sleep(0.05)
            raise AssertionError("request.json was not created in time")

        worker = threading.Thread(target=write_transient_response, daemon=True)
        worker.start()

        response = send_command(automation_dir, "ping", {"value": 2}, timeout_seconds=5)

        worker.join(timeout=1)
        self.assertFalse(worker.is_alive())
        self.assertTrue(response["ok"])
        self.assertEqual("ping", response["command"])
        self.assertEqual({"echo": {"value": 2}}, response["data"])

    def test_send_command_retries_when_response_file_is_temporarily_locked(self) -> None:
        root = self.make_workspace("tmp_automation_send_command_locked")
        automation_dir = root / "automation"
        automation_dir.mkdir(parents=True, exist_ok=True)
        response_path = automation_dir / "response.json"
        request_path = automation_dir / "request.json"

        original_read_text = Path.read_text
        state = {"locked": False}

        def fake_read_text(path: Path, *args, **kwargs) -> str:
            if path == response_path and not state["locked"]:
                state["locked"] = True
                raise PermissionError("response.json is temporarily locked")
            return original_read_text(path, *args, **kwargs)

        def write_matching_response() -> None:
            deadline = time.time() + 5
            while time.time() < deadline:
                if request_path.exists():
                    request = json.loads(request_path.read_text(encoding="utf-8"))
                    write_json_atomically(
                        response_path,
                        {
                            "ok": True,
                            "request_id": request["id"],
                            "command": request["command"],
                            "data": {"echo": request["payload"]},
                        },
                    )
                    return
                time.sleep(0.05)
            raise AssertionError("request.json was not created in time")

        worker = threading.Thread(target=write_matching_response, daemon=True)
        worker.start()

        with (
            patch.object(Path, "read_text", autospec=True, side_effect=fake_read_text),
        ):
            response = send_command(automation_dir, "ping", {"value": 3}, timeout_seconds=5)

        worker.join(timeout=1)
        self.assertFalse(worker.is_alive())
        self.assertTrue(state["locked"])
        self.assertTrue(response["ok"])
        self.assertEqual("ping", response["command"])

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
