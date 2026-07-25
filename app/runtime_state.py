from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class RoomRuntimeState:
    url: str
    consecutive_failures: int = 0
    checks: int = 0
    successes: int = 0
    next_check_at: float = 0.0
    last_check_at: float = 0.0
    last_success_at: float = 0.0
    last_error_category: str = ""

    def record_success(self, *, now: float, poll_seconds: float) -> None:
        self.checks += 1
        self.successes += 1
        self.consecutive_failures = 0
        self.last_check_at = now
        self.last_success_at = now
        self.last_error_category = ""
        self.next_check_at = now + poll_seconds

    def record_failure(self, *, now: float, category: str, delay: float) -> None:
        self.checks += 1
        self.consecutive_failures += 1
        self.last_check_at = now
        self.last_error_category = category
        self.next_check_at = now + delay


@dataclass
class FfmpegCrashTracker:
    window_seconds: float = 1800.0
    clock: Callable[[], float] = time.time
    total_crashes: int = 0
    consecutive_crashes: int = 0
    last_successful_recording_at: float = 0.0
    _crashes: deque[float] = field(default_factory=deque)

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._crashes and self._crashes[0] < cutoff:
            self._crashes.popleft()

    def record_crash(self, *, now: float | None = None) -> None:
        timestamp = self.clock() if now is None else now
        self.total_crashes += 1
        self.consecutive_crashes += 1
        self._crashes.append(timestamp)
        self._prune(timestamp)

    def record_success(self, *, now: float | None = None) -> None:
        timestamp = self.clock() if now is None else now
        self.consecutive_crashes = 0
        self.last_successful_recording_at = timestamp
        self._prune(timestamp)

    def snapshot(self, *, now: float | None = None) -> dict[str, int | float]:
        timestamp = self.clock() if now is None else now
        self._prune(timestamp)
        return {
            "ffmpeg_crashes": len(self._crashes),
            "ffmpeg_crashes_window": len(self._crashes),
            "ffmpeg_crashes_total": self.total_crashes,
            "ffmpeg_consecutive_crashes": self.consecutive_crashes,
            "ffmpeg_crash_window_seconds": self.window_seconds,
            "last_successful_recording_at": self.last_successful_recording_at,
        }
