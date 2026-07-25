from scripts.docker_long_run_validate import summarize


def test_long_run_summary_tracks_growth_restarts_and_probe() -> None:
    samples = [
        {
            "container_restart_count": 2,
            "room_checks_total": 10,
            "room_check_successes": 9,
            "room_check_success_rate": 0.9,
            "ffmpeg_crashes_total": 1,
            "active_recordings": 1,
            "disk_bytes": 100,
            "ffmpeg_processes": 1,
        },
        {
            "container_restart_count": 3,
            "room_checks_total": 20,
            "room_check_successes": 18,
            "room_check_success_rate": 0.9,
            "ffmpeg_crashes_total": 2,
            "network_error_categories": {"network_timeout": 2},
            "active_recordings": 2,
            "disk_bytes": 350,
            "ffmpeg_processes": 2,
        },
    ]
    result = summarize(samples, {"probeable": True})
    assert result["container_restart_delta"] == 1
    assert result["disk_growth_bytes"] == 250
    assert result["max_active_recordings"] == 2
    assert result["latest_ts"]["probeable"] is True
