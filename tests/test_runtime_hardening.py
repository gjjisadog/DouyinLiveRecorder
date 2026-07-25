from __future__ import annotations

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

from app.config import load_config
from app.douyin_daemon import DouyinDaemon
from app.models import RoomConfig
from app.runtime_state import FfmpegCrashTracker, RoomRuntimeState
from src.http_clients.async_http import async_req, use_async_client


def _daemon(tmp_path: Path, *, rooms: int = 1) -> DouyinDaemon:
    room_lines = "\n".join(
        f"  - url: https://live.douyin.com/{index}" for index in range(rooms)
    )
    config_path = tmp_path / "douyin.yaml"
    config_path.write_text(
        f"""rooms:
{room_lines}
recorder:
  poll_seconds: 10
  max_concurrent_checks: 3
storage:
  path: {tmp_path.as_posix()}/downloads
  state_path: {tmp_path.as_posix()}/state
  min_free_gb: 0.1
""",
        encoding="utf-8",
    )
    return DouyinDaemon(load_config(config_path), config_path=config_path)


def test_multi_room_checks_run_concurrently(tmp_path: Path) -> None:
    daemon = _daemon(tmp_path, rooms=2)
    completed: list[str] = []

    async def resolve(room: RoomConfig, _config=None):
        if room.url.endswith("/0"):
            await asyncio.sleep(0.2)
        else:
            await asyncio.sleep(0.01)
        completed.append(room.url)
        return room, {"is_live": False}

    async def exercise() -> None:
        daemon._resolve = resolve  # type: ignore[method-assign]
        semaphore = asyncio.Semaphore(2)
        config = daemon.config
        await asyncio.gather(
            *(daemon._check_room(room, config, semaphore) for room in config.rooms)
        )

    asyncio.run(exercise())
    assert completed[0].endswith("/1")
    assert all(state.successes == 1 for state in daemon.room_states.values())
    daemon.postprocess.shutdown(wait=True)


def test_shared_http_client_is_reused_without_constructing_fallback() -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(200, text="ok")

    async def exercise() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with use_async_client(client):
                with patch("src.http_clients.async_http.httpx.AsyncClient") as constructor:
                    assert await async_req("https://example.test/one") == "ok"
                    assert await async_req("https://example.test/two") == "ok"
                    constructor.assert_not_called()

    asyncio.run(exercise())
    assert requests == ["https://example.test/one", "https://example.test/two"]


def test_daemon_closes_shared_http_client(tmp_path: Path) -> None:
    daemon = _daemon(tmp_path)
    client = AsyncMock()

    async def stop_scheduler() -> None:
        daemon.shutdown_event.set()

    with (
        patch.object(daemon, "_make_http_client", return_value=client),
        patch.object(daemon, "_scheduler", side_effect=stop_scheduler),
    ):
        asyncio.run(daemon.run_async())

    client.aclose.assert_awaited_once()


def test_room_backoff_is_independent_and_success_resets_failures() -> None:
    first = RoomRuntimeState("one")
    second = RoomRuntimeState("two")
    first.record_failure(now=10, category="network_timeout", delay=5)
    first.record_failure(now=20, category="network_timeout", delay=10)
    second.record_failure(now=10, category="risk_control", delay=5)

    assert first.consecutive_failures == 2
    assert first.next_check_at == 30
    assert second.consecutive_failures == 1
    assert second.next_check_at == 15

    first.record_success(now=31, poll_seconds=120)
    assert first.consecutive_failures == 0
    assert first.next_check_at == 151
    assert second.consecutive_failures == 1


def test_ffmpeg_crash_tracker_uses_sliding_window_and_keeps_history() -> None:
    tracker = FfmpegCrashTracker(window_seconds=60)
    tracker.record_crash(now=0)
    tracker.record_crash(now=10)
    tracker.record_crash(now=80)

    snapshot = tracker.snapshot(now=80)
    assert snapshot["ffmpeg_crashes_window"] == 1
    assert snapshot["ffmpeg_crashes_total"] == 3
    assert snapshot["ffmpeg_consecutive_crashes"] == 3

    tracker.record_success(now=90)
    snapshot = tracker.snapshot(now=90)
    assert snapshot["ffmpeg_consecutive_crashes"] == 0
    assert snapshot["last_successful_recording_at"] == 90
