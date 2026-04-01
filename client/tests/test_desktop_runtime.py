from __future__ import annotations

import json
import os
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from client.infra.process.desktop_runtime import DesktopRuntimeService, DesktopRuntimeState


class _FakeStartupAdapter:
    def __init__(self) -> None:
        self.entries: dict[str, str] = {}

    def is_enabled(self, name: str) -> bool:
        return name in self.entries

    def enable(self, name: str, command: str) -> None:
        self.entries[name] = command

    def disable(self, name: str) -> None:
        self.entries.pop(name, None)


class DesktopRuntimeServiceTests(unittest.TestCase):
    def make_workspace(self, prefix: str) -> Path:
        root = Path.cwd() / f"{prefix}_{uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def test_mark_launch_started_and_clean_exit_persist_runtime_state(self) -> None:
        root = self.make_workspace("tmp_desktop_runtime")
        runtime_state_path = root / "client_data" / "runtime_state.json"
        service = DesktopRuntimeService(
            runtime_state_path=runtime_state_path,
            startup_name="DouyinLiveRecorder Client",
            startup_command='"client.exe"',
            startup_adapter=_FakeStartupAdapter(),
        )
        service.save_state(
            DesktopRuntimeState(
                last_exit_clean=True,
                running_task_ids=["task-001", "task-001", "task-002"],
                scheduler_running=False,
                current_tab_index=2,
                hidden_to_tray=True,
            )
        )

        previous_state = service.mark_launch_started()

        self.assertTrue(previous_state.last_exit_clean)
        self.assertEqual(["task-001", "task-002"], previous_state.running_task_ids)
        saved_payload = json.loads(runtime_state_path.read_text(encoding="utf-8"))
        self.assertFalse(saved_payload["last_exit_clean"])
        self.assertEqual(["task-001", "task-002"], saved_payload["running_task_ids"])
        self.assertFalse(saved_payload["scheduler_running"])
        self.assertEqual(2, saved_payload["current_tab_index"])
        self.assertTrue(saved_payload["hidden_to_tray"])
        self.assertTrue(saved_payload["updated_at"])

        service.mark_clean_exit(
            DesktopRuntimeState(
                last_exit_clean=False,
                running_task_ids=["task-002"],
                scheduler_running=False,
                current_tab_index=1,
                hidden_to_tray=False,
            )
        )

        final_payload = json.loads(runtime_state_path.read_text(encoding="utf-8"))
        self.assertTrue(final_payload["last_exit_clean"])
        self.assertEqual(["task-002"], final_payload["running_task_ids"])
        self.assertFalse(final_payload["scheduler_running"])
        self.assertEqual(1, final_payload["current_tab_index"])
        self.assertFalse(final_payload["hidden_to_tray"])
        self.assertTrue(final_payload["updated_at"])

    def test_apply_startup_setting_round_trip_uses_adapter_state(self) -> None:
        adapter = _FakeStartupAdapter()
        service = DesktopRuntimeService(
            runtime_state_path=Path("unused.json"),
            startup_name="DouyinLiveRecorder Client",
            startup_command='"client.exe" --hidden',
            startup_adapter=adapter,
        )

        enabled = service.apply_startup_setting(True)

        self.assertTrue(enabled)
        self.assertEqual('"client.exe" --hidden', adapter.entries["DouyinLiveRecorder Client"])
        self.assertTrue(service.is_startup_enabled())

        disabled = service.apply_startup_setting(False)

        self.assertFalse(disabled)
        self.assertFalse(service.is_startup_enabled())


if __name__ == "__main__":
    unittest.main()
