from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def run_command(command: Sequence[str], *, timeout: float = 60) -> CommandResult:
    completed = subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    return CommandResult(completed.returncode, completed.stdout.strip(), completed.stderr.strip())


def _json_or_empty(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _integer(value: str) -> int:
    try:
        return int(value.strip())
    except (AttributeError, ValueError):
        return 0


def collect_sample(container: str) -> dict[str, Any]:
    inspect = run_command(
        [
            "docker",
            "inspect",
            "--format",
            "{{json .}}",
            container,
        ]
    )
    inspection = _json_or_empty(inspect.stdout)
    state = inspection.get("State") if isinstance(inspection.get("State"), dict) else {}
    health_result = run_command(["docker", "exec", container, "cat", "/data/state/health.json"])
    health = _json_or_empty(health_result.stdout)
    stats_result = run_command(
        ["docker", "stats", "--no-stream", "--format", "{{json .}}", container]
    )
    stats = _json_or_empty(stats_result.stdout)
    disk_result = run_command(
        ["docker", "exec", container, "du", "-sb", "/data/downloads", "/data/state"]
    )
    disk_bytes = 0
    for line in disk_result.stdout.splitlines():
        fields = line.split(maxsplit=1)
        if fields:
            disk_bytes += _integer(fields[0])
    ffmpeg_result = run_command(
        [
            "docker",
            "exec",
            container,
            "python",
            "-c",
            (
                "from pathlib import Path;"
                "print(sum(1 for p in Path('/proc').glob('[0-9]*/comm') "
                "if p.read_text(errors='ignore').strip() == 'ffmpeg'))"
            ),
        ]
    )
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "container_running": bool(state.get("Running")),
        "container_pid": int(state.get("Pid") or 0),
        "container_restart_count": int(inspection.get("RestartCount") or 0),
        "container_health": (state.get("Health") or {}).get("Status", ""),
        "room_checks_total": int(health.get("room_checks_total") or 0),
        "room_check_successes": int(health.get("room_check_successes") or 0),
        "room_check_success_rate": float(health.get("room_check_success_rate") or 0),
        "ffmpeg_crashes_window": int(health.get("ffmpeg_crashes_window") or 0),
        "ffmpeg_crashes_total": int(health.get("ffmpeg_crashes_total") or 0),
        "ffmpeg_consecutive_crashes": int(health.get("ffmpeg_consecutive_crashes") or 0),
        "network_error_categories": health.get("check_failure_categories") or {},
        "active_recordings": int(health.get("active_recordings") or 0),
        "cpu_percent": stats.get("CPUPerc", ""),
        "memory_usage": stats.get("MemUsage", ""),
        "memory_percent": stats.get("MemPerc", ""),
        "disk_bytes": disk_bytes,
        "ffmpeg_processes": _integer(ffmpeg_result.stdout),
    }


def probe_latest_ts(container: str) -> dict[str, Any]:
    script = (
        "import json,subprocess;"
        "from pathlib import Path;"
        "files=list(Path('/data/downloads').rglob('*.ts'));"
        "latest=max(files,key=lambda p:p.stat().st_mtime) if files else None;"
        "result={'file':str(latest) if latest else '', 'probeable':False};"
        "p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',"
        "'-of','json',str(latest)],capture_output=True,text=True) if latest else None;"
        "result.update({'probeable':bool(p and p.returncode==0),"
        "'ffprobe_returncode':p.returncode if p else None,"
        "'ffprobe_error':p.stderr[-500:] if p else 'no TS files'});"
        "print(json.dumps(result,ensure_ascii=False))"
    )
    result = run_command(["docker", "exec", container, "python", "-c", script], timeout=90)
    payload = _json_or_empty(result.stdout)
    if not payload:
        payload = {"file": "", "probeable": False, "ffprobe_error": result.stderr[-500:]}
    return payload


def summarize(samples: list[dict[str, Any]], probe: dict[str, Any]) -> dict[str, Any]:
    first = samples[0] if samples else {}
    last = samples[-1] if samples else {}
    return {
        "sample_count": len(samples),
        "container_restart_delta": max(
            0,
            int(last.get("container_restart_count", 0))
            - int(first.get("container_restart_count", 0)),
        ),
        "room_checks_total": int(last.get("room_checks_total", 0)),
        "room_check_successes": int(last.get("room_check_successes", 0)),
        "room_check_success_rate": float(last.get("room_check_success_rate", 0)),
        "ffmpeg_crashes_total": int(last.get("ffmpeg_crashes_total", 0)),
        "network_error_categories": last.get("network_error_categories", {}),
        "max_active_recordings": max(
            (int(sample.get("active_recordings", 0)) for sample in samples),
            default=0,
        ),
        "disk_growth_bytes": max(
            0, int(last.get("disk_bytes", 0)) - int(first.get("disk_bytes", 0))
        ),
        "max_ffmpeg_processes": max(
            (int(sample.get("ffmpeg_processes", 0)) for sample in samples),
            default=0,
        ),
        "latest_ts": probe,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repeatable Docker daemon 24/72-hour validation")
    duration = parser.add_mutually_exclusive_group(required=True)
    duration.add_argument("--hours", type=int, choices=(24, 72))
    duration.add_argument("--duration-seconds", type=float, help="short smoke run for script testing")
    parser.add_argument("--compose-file", default="docker-compose.yaml")
    parser.add_argument("--container", default="douyin-recorder")
    parser.add_argument("--interval", type=float, default=60.0)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--no-start", action="store_true")
    parser.add_argument("--stop-at-end", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    duration_seconds = args.duration_seconds or args.hours * 3600
    if duration_seconds <= 0 or args.interval <= 0:
        raise SystemExit("duration and interval must be positive")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = args.output_dir or Path("artifacts") / "long-run" / stamp
    output_dir.mkdir(parents=True, exist_ok=True)
    samples_file = output_dir / "samples.jsonl"

    if not args.no_start:
        started = run_command(
            ["docker", "compose", "-f", args.compose_file, "up", "-d"],
            timeout=600,
        )
        if started.returncode:
            print(started.stderr, file=sys.stderr)
            return 2

    samples: list[dict[str, Any]] = []
    deadline = time.monotonic() + duration_seconds
    try:
        while True:
            sample = collect_sample(args.container)
            samples.append(sample)
            with samples_file.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(sample, ensure_ascii=False) + "\n")
            if time.monotonic() >= deadline:
                break
            time.sleep(min(args.interval, max(0.0, deadline - time.monotonic())))
    except KeyboardInterrupt:
        print("validation interrupted; partial results retained", file=sys.stderr)

    probe = probe_latest_ts(args.container)
    summary = summarize(samples, probe)
    if args.stop_at_end:
        stopped = run_command(["docker", "stop", args.container], timeout=120)
        after = run_command(
            ["docker", "inspect", "--format", "{{json .State}}", args.container]
        )
        stopped_state = _json_or_empty(after.stdout)
        summary["stop"] = {
            "returncode": stopped.returncode,
            "container_running": bool(stopped_state.get("Running")),
            "container_pid": int(stopped_state.get("Pid") or 0),
            "residual_processes": int(stopped_state.get("Pid") or 0) != 0,
        }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
