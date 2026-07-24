from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


def build_ffmpeg_command(
    input_url: str,
    output_template: Path,
    *,
    segment_seconds: int = 1800,
    proxy_url: str = "",
    headers: str = "",
) -> list[str]:
    command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "warning", "-y"]
    if proxy_url:
        command.extend(["-http_proxy", proxy_url])
    if headers:
        command.extend(["-headers", headers])
    command.extend(
        [
            "-rw_timeout",
            "30000000",
            "-i",
            input_url,
            "-map",
            "0",
            "-c",
            "copy",
            "-f",
            "segment",
            "-segment_time",
            str(segment_seconds),
            "-reset_timestamps",
            "1",
            "-segment_format",
            "mpegts",
            str(output_template),
        ]
    )
    return command


@dataclass
class ManagedProcess:
    key: str
    process: subprocess.Popen[str]
    command: tuple[str, ...]
    errors: deque[str] = field(default_factory=lambda: deque(maxlen=50))
    return_code: int | None = None


class ProcessManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._processes: dict[str, ManagedProcess] = {}

    def start(self, key: str, command: Iterable[str]) -> ManagedProcess:
        with self._lock:
            if key in self._processes and self._processes[key].process.poll() is None:
                raise RuntimeError(f"录制任务已在运行: {key}")
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
            process = subprocess.Popen(
                list(command),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )
            managed = ManagedProcess(key, process, tuple(command))
            self._processes[key] = managed
        threading.Thread(target=self._collect_errors, args=(managed,), daemon=True).start()
        return managed

    @staticmethod
    def _collect_errors(managed: ManagedProcess) -> None:
        if managed.process.stderr is None:
            return
        for line in managed.process.stderr:
            managed.errors.append(line.rstrip())

    def wait(self, key: str) -> int:
        with self._lock:
            managed = self._processes[key]
        return_code = managed.process.wait()
        managed.return_code = return_code
        with self._lock:
            self._processes.pop(key, None)
        return return_code

    def active_keys(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(
                key for key, managed in self._processes.items() if managed.process.poll() is None
            )

    @staticmethod
    def _send_interrupt(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.send_signal(signal.SIGINT)

    def stop_all(self, interrupt_timeout: float = 30.0, terminate_timeout: float = 15.0) -> None:
        with self._lock:
            processes = list(self._processes.values())
        for managed in processes:
            try:
                self._send_interrupt(managed.process)
            except ProcessLookupError:
                pass
        self._wait_then_escalate(processes, interrupt_timeout, "terminate")
        self._wait_then_escalate(processes, terminate_timeout, "kill")
        for managed in processes:
            try:
                managed.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                managed.process.kill()

    @staticmethod
    def _wait_then_escalate(
        processes: list[ManagedProcess], timeout: float, action: str
    ) -> None:
        deadline = time.monotonic() + timeout
        for managed in processes:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                managed.process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                getattr(managed.process, action)()
