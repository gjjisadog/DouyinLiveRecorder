from __future__ import annotations

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
