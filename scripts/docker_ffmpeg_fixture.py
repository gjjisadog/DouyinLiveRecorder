"""Container-only fixture used to verify graceful FFmpeg shutdown and TS integrity."""

from __future__ import annotations

import signal
import threading
import time
from pathlib import Path

from app.process_manager import ProcessManager


def main() -> int:
    output_dir = Path("/data/downloads")
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "fixture_%03d.ts"
    manager = ProcessManager()
    stopping = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stopping.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, request_stop)

    command = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "warning",
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
    manager.start("fixture", command)
    waiter = threading.Thread(target=manager.wait, args=("fixture",), daemon=True)
    waiter.start()
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if list(output_dir.glob("fixture_*.ts")):
            (output_dir / "fixture.ready").write_text("ready\n", encoding="utf-8")
            break
        time.sleep(0.1)
    else:
        manager.stop_all()
        return 2

    stopping.wait()
    manager.stop_all(interrupt_timeout=30, terminate_timeout=30)
    waiter.join(timeout=10)
    return 0 if not manager.active_keys() else 3


if __name__ == "__main__":
    raise SystemExit(main())
