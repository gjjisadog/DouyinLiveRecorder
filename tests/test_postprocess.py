from __future__ import annotations

import shutil
import subprocess
import threading
from pathlib import Path

import pytest

from app.postprocess import PostProcessQueue
from app.process_manager import ProcessManager, build_remux_command


def test_remux_command_uses_stream_copy_and_explicit_mp4(tmp_path: Path) -> None:
    command = build_remux_command(tmp_path / "input.ts", tmp_path / "output.mp4.partial")
    assert command[0] == "ffmpeg"
    assert command[command.index("-c") + 1] == "copy"
    assert command[command.index("-f") + 1] == "mp4"
    assert "+faststart" in command


@pytest.mark.integration
def test_postprocess_queue_remuxes_without_deleting_source(tmp_path: Path) -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg and ffprobe are required")
    source = tmp_path / "sample.ts"
    generated = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=160x120:rate=15",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-f",
            "mpegts",
            str(source),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert generated.returncode == 0, generated.stderr
    queue = PostProcessQueue(
        ProcessManager(),
        workers=1,
        delete_source=False,
        stopping=threading.Event(),
    )
    assert queue.submit(source)
    queue.shutdown(wait=True)
    output = source.with_suffix(".mp4")
    assert source.is_file()
    assert output.is_file()
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=format_name", str(output)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert probe.returncode == 0, probe.stderr
    assert "mp4" in probe.stdout


def test_postprocess_rejects_work_after_shutdown(tmp_path: Path) -> None:
    source = tmp_path / "sample.ts"
    source.touch()
    stopping = threading.Event()
    stopping.set()
    queue = PostProcessQueue(
        ProcessManager(),
        workers=1,
        delete_source=False,
        stopping=stopping,
    )
    assert queue.submit(source) is False
    queue.shutdown()

