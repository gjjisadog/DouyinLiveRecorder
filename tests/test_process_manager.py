from __future__ import annotations

import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

from app.process_manager import ProcessManager, build_ffmpeg_command


def test_ffmpeg_command_uses_segmented_ts_and_stream_copy(tmp_path: Path) -> None:
    command = build_ffmpeg_command(
        "https://example/live.flv",
        tmp_path / "out_%03d.ts",
        segment_seconds=1800,
        proxy_url="http://127.0.0.1:7890",
    )
    assert command[0] == "ffmpeg"
    assert ["-c", "copy"] == command[command.index("-c") : command.index("-c") + 2]
    assert ["-segment_time", "1800"] == command[
        command.index("-segment_time") : command.index("-segment_time") + 2
    ]
    assert "-http_proxy" in command
    assert str(command[-1]).endswith(".ts")


def test_posix_stop_signals_the_entire_ffmpeg_process_group() -> None:
    process = Mock(spec=subprocess.Popen)
    process.pid = 4321
    process.poll.return_value = None
    with (
        patch("app.process_manager.os.name", "posix"),
        patch("app.process_manager.os.getpgid", return_value=4321, create=True),
        patch("app.process_manager.os.killpg", create=True) as killpg,
    ):
        ProcessManager._send_interrupt(process)
        ProcessManager._terminate_process_group(process)
        ProcessManager._kill_process_group(process)

    expected_calls = [
        call(4321, signal_number)
        for signal_number in (
            signal.SIGINT,
            signal.SIGTERM,
            getattr(signal, "SIGKILL", getattr(signal, "SIGBREAK", signal.SIGTERM)),
        )
    ]
    assert killpg.call_args_list == expected_calls


@pytest.mark.integration
def test_interrupted_ffmpeg_writes_probeable_ts(tmp_path: Path) -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg and ffprobe are required")
    output = tmp_path / "local_%03d.ts"
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-re",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=size=320x240:rate=25",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=1000:sample_rate=48000",
        "-c:v",
        "mpeg2video",
        "-c:a",
        "mp2",
        "-f",
        "segment",
        "-segment_time",
        "30",
        "-reset_timestamps",
        "1",
        str(output),
    ]
    manager = ProcessManager()
    manager.start("local", command)
    waiter = threading.Thread(target=manager.wait, args=("local",))
    waiter.start()
    deadline = time.time() + 10
    while time.time() < deadline and not list(tmp_path.glob("*.ts")):
        time.sleep(0.1)
    time.sleep(1)
    manager.stop_all(interrupt_timeout=10, terminate_timeout=5)
    waiter.join(timeout=10)
    files = sorted(tmp_path.glob("*.ts"))
    assert files
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(files[-1]),
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert probe.returncode == 0, probe.stderr
    assert float(probe.stdout.strip()) > 0
    assert not manager.active_keys()
