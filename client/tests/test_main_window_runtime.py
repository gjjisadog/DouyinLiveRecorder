from __future__ import annotations

import os
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from client.app_settings import AppSettings
from client.core.models import AppConfig, RecordTask
from client.infra.process.desktop_runtime import DesktopRuntimeState
from client.ui.main_window import MainWindow
from client.viewmodels.settings_viewmodel import SettingsViewModel
from client.viewmodels.task_viewmodel import TaskViewModel


class _FakeTrayIcon:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []
        self.hidden = False

    def showMessage(self, title: str, message: str, *_args) -> None:
        self.messages.append((title, message))

    def hide(self) -> None:
        self.hidden = True


class _FakeDesktopRuntimeService:
    def __init__(self) -> None:
        self.saved_states: list[DesktopRuntimeState] = []
        self.clean_exit_states: list[DesktopRuntimeState] = []

    def save_state(self, state: DesktopRuntimeState) -> None:
        self.saved_states.append(state)

    def mark_clean_exit(self, state: DesktopRuntimeState) -> None:
        self.clean_exit_states.append(state)


class _FakeRecordManager:
    def __init__(self, tasks: list[RecordTask]) -> None:
        self.tasks = {task.task_id: task for task in tasks}
        self.start_calls: list[str] = []
        self.log_handler = None

    def set_log_handler(self, handler) -> None:
        self.log_handler = handler

    def get_task(self, task_id: str) -> RecordTask | None:
        return self.tasks.get(task_id)

    def start_task(self, task_id: str) -> None:
        self.start_calls.append(task_id)

    def sync_task_states(self) -> bool:
        return False


class MainWindowRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def make_workspace(self, prefix: str) -> Path:
        root = Path.cwd() / f"{prefix}_{uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def create_window(
        self,
        *,
        config: AppConfig,
        tasks: list[RecordTask] | None = None,
        startup_state: DesktopRuntimeState | None = None,
        desktop_runtime_service: _FakeDesktopRuntimeService | None = None,
    ) -> MainWindow:
        root = self.make_workspace("tmp_main_window_runtime")
        tasks = tasks or []
        record_manager = _FakeRecordManager(tasks)
        window = MainWindow(
            settings=AppSettings(data_dir=root / "client_data"),
            task_viewmodel=TaskViewModel(tasks=tasks),
            settings_viewmodel=SettingsViewModel(config=config),
            record_manager=record_manager,
            desktop_runtime_service=desktop_runtime_service,
            startup_state=startup_state or DesktopRuntimeState(),
        )
        window.tasks_page._status_timer.stop()
        window._scheduler_timer.stop()
        window._runtime_timer.stop()
        self.addCleanup(window.deleteLater)
        return window

    def test_close_event_hides_window_when_close_to_tray_is_enabled(self) -> None:
        runtime_service = _FakeDesktopRuntimeService()
        window = self.create_window(
            config=AppConfig(close_to_tray=True, minimize_to_tray=False),
            desktop_runtime_service=runtime_service,
        )
        tray_icon = _FakeTrayIcon()
        window._tray_icon = tray_icon

        window.show()
        self.app.processEvents()
        window.close()
        self.app.processEvents()

        self.assertFalse(window.isVisible())
        self.assertTrue(tray_icon.messages)
        self.assertTrue(runtime_service.saved_states)
        self.assertFalse(runtime_service.clean_exit_states)

        window._allow_close = True
        window.close()
        self.app.processEvents()

        self.assertTrue(tray_icon.hidden)
        self.assertEqual(1, len(runtime_service.clean_exit_states))
        self.assertTrue(runtime_service.clean_exit_states[0].last_exit_clean)

    def test_apply_startup_state_restores_tasks_and_hidden_window(self) -> None:
        runtime_service = _FakeDesktopRuntimeService()
        task = RecordTask(task_id="task-restore", url="https://live.example.com/1")
        window = self.create_window(
            config=AppConfig(restore_tasks_on_launch=True, restore_window_on_launch=True),
            tasks=[task],
            desktop_runtime_service=runtime_service,
        )
        tray_icon = _FakeTrayIcon()
        window._tray_icon = tray_icon
        window.startup_state = DesktopRuntimeState(
            last_exit_clean=False,
            running_task_ids=[task.task_id],
            scheduler_running=True,
            current_tab_index=3,
            hidden_to_tray=True,
        )

        window.show()
        self.app.processEvents()
        window._apply_startup_state()
        self.app.processEvents()

        self.assertEqual(3, window.tabs.currentIndex())
        self.assertEqual([task.task_id], window.record_manager.start_calls)
        self.assertFalse(window.isVisible())
        self.assertTrue(runtime_service.saved_states)


if __name__ == "__main__":
    unittest.main()
