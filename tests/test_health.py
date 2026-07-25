from __future__ import annotations

import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
import time
from pathlib import Path

from app.health import HealthState, check


def test_healthcheck_reads_shared_state_without_reparsing_invalid_live_config(
    tmp_path: Path,
) -> None:
    config = tmp_path / "douyin.yaml"
    config.write_text("rooms: [temporarily-invalid\n", encoding="utf-8")
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    state_path = tmp_path / "state"
    now = time.time()
    health = HealthState(state_path)
    health.update(
        heartbeat_at=now,
        last_check_at=now,
        stopping=False,
        ffmpeg_crashes=0,
        storage_path=str(downloads),
        min_free_gb=0.1,
        poll_seconds=10,
    )

    healthy, message = check(config, state_path)

    assert healthy
    assert message == "healthy"


def test_health_state_concurrent_thread_and_async_writes_are_atomic(tmp_path: Path) -> None:
    health = HealthState(tmp_path / "state")

    def write_thread(index: int) -> None:
        health.update(**{f"thread_{index}": index})

    async def write_async() -> None:
        await asyncio.gather(
            *(health.update_async(**{f"async_{index}": index}) for index in range(20))
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(write_thread, index) for index in range(20)]
        asyncio.run(write_async())
        for future in futures:
            future.result()

    payload = json.loads(health.path.read_text(encoding="utf-8"))
    assert all(payload[f"thread_{index}"] == index for index in range(20))
    assert all(payload[f"async_{index}"] == index for index in range(20))
    assert not list(health.path.parent.glob(".health.json.*.tmp"))
    if os.name != "nt":
        assert health.path.stat().st_mode & 0o777 == 0o644


def test_healthcheck_uses_sliding_window_not_lifetime_total(tmp_path: Path) -> None:
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    state_path = tmp_path / "state"
    now = time.time()
    health = HealthState(state_path)
    health.update(
        heartbeat_at=now,
        last_check_at=now,
        stopping=False,
        ffmpeg_crashes=0,
        ffmpeg_crashes_window=0,
        ffmpeg_crashes_total=100,
        storage_path=str(downloads),
        min_free_gb=0.1,
        poll_seconds=10,
    )
    assert check(tmp_path / "missing.yaml", state_path) == (True, "healthy")
