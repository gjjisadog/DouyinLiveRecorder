from __future__ import annotations

import signal
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, call, patch

from client.infra.docker.launcher import KILL_SIGNAL, DockerLauncher


def test_launcher_has_only_the_daemon_recorder_entrypoint() -> None:
    with patch.dict("os.environ", {}, clear=True):
        launcher = DockerLauncher(Path("/app"))
    assert launcher._recorder_command() == [sys.executable, "-m", "app.douyin_daemon"]
    assert "main.py" not in " ".join(launcher._recorder_command())


def test_start_recorder_uses_an_independent_posix_process_group() -> None:
    with patch.dict("os.environ", {}, clear=True):
        launcher = DockerLauncher(Path("/app"))
    child = Mock()
    with (
        patch("client.infra.docker.launcher.os.name", "posix"),
        patch("client.infra.docker.launcher.subprocess.Popen", return_value=child) as popen,
    ):
        launcher._start_recorder()
    _, kwargs = popen.call_args
    assert kwargs["start_new_session"] is True
    assert kwargs["cwd"] == Path("/app")


def test_stop_escalates_daemon_sigint_then_terminate_then_kill() -> None:
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
    assert send_signal.call_args_list == [
        call(child, signal.SIGINT),
        call(child, signal.SIGTERM),
        call(child, KILL_SIGNAL),
    ]
    assert wait_child.call_args_list == [call(child, 1.0), call(child, 2.0), call(child, 3.0)]


def test_stop_rejects_writes_before_notifying_daemon_and_waiting_for_web() -> None:
    with patch.dict("os.environ", {}, clear=True):
        launcher = DockerLauncher(Path("/app"))
    events: list[str] = []
    launcher.server = Mock()
    launcher.server.stop_accepting_writes.side_effect = lambda: events.append("reject-writes")
    launcher.server.shutdown.side_effect = lambda: events.append("web-shutdown")
    launcher.server.server_close.side_effect = lambda: events.append("web-close")
    launcher.server_thread = Mock()
    launcher.server_thread.join.side_effect = lambda timeout: events.append("web-join")
    with patch.object(launcher, "_stop_child", side_effect=lambda: events.append("daemon-stop")):
        launcher.stop()
    assert events == ["reject-writes", "web-shutdown", "daemon-stop", "web-close", "web-join"]
