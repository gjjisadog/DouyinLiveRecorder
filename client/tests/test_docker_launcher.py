from __future__ import annotations

import signal
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from client.infra.docker.launcher import KILL_SIGNAL, DockerLauncher


class DockerLauncherTests(unittest.TestCase):
    def test_daemon_is_the_default_recorder_and_legacy_remains_available(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            launcher = DockerLauncher(Path("/app"))
        self.assertEqual([sys.executable, "-m", "app.douyin_daemon"], launcher._recorder_command())

        with patch.dict("os.environ", {"DLR_RECORDER_MODE": "legacy"}, clear=True):
            legacy_launcher = DockerLauncher(Path("/app"))
        self.assertEqual([sys.executable, "main.py"], legacy_launcher._recorder_command())

    def test_start_recorder_uses_an_independent_posix_process_group(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            launcher = DockerLauncher(Path("/app"))
        child = Mock()
        with (
            patch("client.infra.docker.launcher.os.name", "posix"),
            patch("client.infra.docker.launcher.subprocess.Popen", return_value=child) as popen,
        ):
            launcher._start_recorder()

        _, kwargs = popen.call_args
        self.assertTrue(kwargs["start_new_session"])
        self.assertEqual(Path("/app"), kwargs["cwd"])

    def test_stop_escalates_sigint_then_terminate_then_kill(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "DLR_STOP_INTERRUPT_TIMEOUT": "1",
                "DLR_STOP_TERMINATE_TIMEOUT": "2",
                "DLR_STOP_KILL_TIMEOUT": "3",
            },
            clear=True,
        ):
            launcher = DockerLauncher(Path("/app"))
        child = Mock(spec=subprocess.Popen)
        child.poll.return_value = None
        launcher.child = child

        with (
            patch.object(launcher, "_send_signal_to_child_group") as send_signal,
            patch.object(launcher, "_wait_for_child", side_effect=[False, False, True]) as wait_child,
        ):
            launcher._stop_child()

        self.assertEqual(
            [
                call(child, signal.SIGINT),
                call(child, signal.SIGTERM),
                call(child, KILL_SIGNAL),
            ],
            send_signal.call_args_list,
        )
        self.assertEqual([call(child, 1.0), call(child, 2.0), call(child, 3.0)], wait_child.call_args_list)
        self.assertIsNone(launcher.child)

    def test_stop_is_idempotent(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            launcher = DockerLauncher(Path("/app"))
        with patch.object(launcher, "_stop_child") as stop_child:
            launcher.stop()
            launcher.stop()
        stop_child.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
