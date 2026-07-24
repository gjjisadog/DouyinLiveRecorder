"""Stress packaged EXE get_logs automation against a local HLS source."""

from __future__ import annotations

import argparse
import json
import os
import socket
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.exe_automation_acceptance import (
    AUTOMATION_ENV,
    detect_ffmpeg_dir,
    prepare_workspace,
    send_command,
    wait_for_history,
    wait_for_task_status,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BL-017 get_logs stability acceptance.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--exe-path", type=Path, default=None)
    parser.add_argument("--stream-url", default=None)
    parser.add_argument("--display-name", default="BL017_GetLogs_Stability")
    parser.add_argument("--source-workspace", type=Path, default=None)
    parser.add_argument("--record-seconds", type=int, default=90)
    parser.add_argument("--query-interval", type=float, default=2.0)
    parser.add_argument("--query-timeout", type=int, default=12)
    parser.add_argument("--startup-timeout", type=int, default=30)
    parser.add_argument("--command-timeout", type=int, default=20)
    parser.add_argument("--log-limit", type=int, default=100)
    parser.add_argument("--split-seconds", type=int, default=86400)
    parser.add_argument("--loop-seconds", type=int, default=300)
    parser.add_argument("--video-bitrate-mbps", type=int, default=24)
    parser.add_argument("--port", type=int, default=None)
    return parser.parse_args()


def start_local_hls_source(repo_root: Path, source_workspace: Path, port: int, video_bitrate_mbps: int) -> subprocess.Popen[str]:
    stdout_path = repo_root / "tmp_bl017_local_hls_stdout.log"
    stderr_path = repo_root / "tmp_bl017_local_hls_stderr.log"
    stdout_handle = stdout_path.open("w", encoding="utf-8")
    stderr_handle = stderr_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [
            str((repo_root / ".client-conda-env" / "python.exe").resolve()),
            "scripts/local_hls_test_source.py",
            "--workspace",
            str(source_workspace),
            "--port",
            str(port),
            "--video-bitrate-mbps",
            str(video_bitrate_mbps),
        ],
        cwd=str(repo_root),
        stdout=stdout_handle,
        stderr=stderr_handle,
        text=True,
    )
    process._codex_stdout_handle = stdout_handle  # type: ignore[attr-defined]
    process._codex_stderr_handle = stderr_handle  # type: ignore[attr-defined]
    return process


def stop_process(process: subprocess.Popen[str] | None, timeout: int = 10) -> None:
    if process is None:
        return
    try:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    finally:
        stdout_handle = getattr(process, "_codex_stdout_handle", None)
        stderr_handle = getattr(process, "_codex_stderr_handle", None)
        if stdout_handle is not None:
            stdout_handle.close()
        if stderr_handle is not None:
            stderr_handle.close()


def choose_port(preferred_port: int | None) -> int:
    candidates: list[int] = []
    if preferred_port is not None:
        candidates.append(preferred_port)
    candidates.extend(range(18080, 18090))
    for port in candidates:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free local port available in 18080-18089 for BL-017 source")


def wait_for_local_source(
    source_workspace: Path,
    *,
    process: subprocess.Popen[str],
    timeout_seconds: int,
) -> dict[str, object]:
    info_path = source_workspace / "source_info.json"
    deadline = time.time() + timeout_seconds
    source_info: dict[str, object] | None = None
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Local HLS source exited early: {process.returncode}")
        if info_path.exists():
            source_info = json.loads(info_path.read_text(encoding="utf-8"))
            stream_url = str(source_info.get("stream_url") or "")
            if stream_url:
                try:
                    with urllib.request.urlopen(stream_url, timeout=2) as response:
                        if response.status == 200 and response.read():
                            return source_info
                except (urllib.error.URLError, TimeoutError, OSError):
                    pass
        time.sleep(0.2)
    raise TimeoutError(f"Timed out waiting for local source startup: {info_path}")


def query_get_logs(
    automation_dir: Path,
    *,
    variants: list[dict[str, object]],
    timeout_seconds: int,
    duration_seconds: int,
    interval_seconds: float,
) -> dict[str, object]:
    deadline = time.time() + duration_seconds
    calls: list[dict[str, object]] = []
    iteration = 0
    while time.time() < deadline:
        variant = variants[iteration % len(variants)]
        started = time.perf_counter()
        error: str | None = None
        ok = False
        entry_count = 0
        try:
            response = send_command(automation_dir, "get_logs", variant, timeout_seconds=timeout_seconds)
            ok = bool(response.get("ok"))
            if ok:
                data = response.get("data") or {}
                entry_count = int(data.get("count") or 0)
            else:
                error = str(response.get("error") or "unknown error")
        except Exception as exc:  # pragma: no cover - acceptance only
            error = str(exc)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        calls.append(
            {
                "iteration": iteration,
                "variant": variant.get("name"),
                "payload": variant.get("payload"),
                "ok": ok,
                "latency_ms": latency_ms,
                "entry_count": entry_count,
                "error": error,
            }
        )
        iteration += 1
        sleep_seconds = min(interval_seconds, max(deadline - time.time(), 0))
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    latencies = [float(item["latency_ms"]) for item in calls]
    failed_calls = [item for item in calls if not item["ok"]]
    return {
        "calls": calls,
        "total_calls": len(calls),
        "successful_calls": len(calls) - len(failed_calls),
        "failed_calls": len(failed_calls),
        "max_latency_ms": max(latencies) if latencies else 0.0,
        "avg_latency_ms": round(statistics.fmean(latencies), 2) if latencies else 0.0,
        "failures": failed_calls,
    }


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    workspace = (args.workspace or (repo_root / "tmp_bl017_get_logs_stability")).resolve()
    use_local_source = not bool(args.stream_url)
    source_workspace = (
        args.source_workspace
        or (repo_root / f"{(args.workspace or Path('tmp_bl017_get_logs_stability')).stem}_source")
    ).resolve()
    port = choose_port(args.port) if use_local_source else None
    exe_path = (args.exe_path or (repo_root / "dist" / "DouyinLiveRecorder Client" / "DouyinLiveRecorder Client.exe")).resolve()
    automation_dir = workspace / "client_data" / "automation"
    stream_url = args.stream_url or f"http://127.0.0.1:{port}/stream.m3u8"

    prepare_workspace(
        workspace,
        max_file_size_gb=1.0,
        split_seconds=args.split_seconds,
        loop_seconds=args.loop_seconds,
    )
    automation_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg_dir = detect_ffmpeg_dir()
    env = os.environ.copy()
    env["PATH"] = str(ffmpeg_dir) + os.pathsep + env.get("PATH", "")
    env[AUTOMATION_ENV] = str(automation_dir)

    subprocess.run(["taskkill", "/IM", "DouyinLiveRecorder Client.exe", "/F"], capture_output=True)

    source_process: subprocess.Popen[str] | None = None
    client_process: subprocess.Popen[bytes] | None = None
    summary: dict[str, object] = {
        "workspace": str(workspace),
        "source_workspace": str(source_workspace) if use_local_source else None,
        "exe_path": str(exe_path),
        "stream_url": stream_url,
        "use_local_source": use_local_source,
        "record_seconds": args.record_seconds,
        "query_interval": args.query_interval,
        "query_timeout": args.query_timeout,
        "log_limit": args.log_limit,
    }

    try:
        if use_local_source:
            if port is None:
                raise RuntimeError("Local source mode requires a chosen port")
            source_process = start_local_hls_source(repo_root, source_workspace, port, args.video_bitrate_mbps)
            summary["source_process_id"] = source_process.pid
            summary["source_port"] = port
            summary["source_info"] = wait_for_local_source(
                source_workspace,
                process=source_process,
                timeout_seconds=args.startup_timeout,
            )

        client_process = subprocess.Popen([str(exe_path)], cwd=str(workspace), env=env)
        summary["client_process_id"] = client_process.pid

        send_command(automation_dir, "ping", {}, timeout_seconds=args.startup_timeout)
        add_response = send_command(
            automation_dir,
            "add_task",
            {
                "url": stream_url,
                "display_name": args.display_name,
                "quality": "原画",
                "enabled": True,
            },
            timeout_seconds=args.command_timeout,
        )
        if not add_response.get("ok"):
            raise RuntimeError(add_response.get("error") or "add_task failed")
        task = add_response["data"]["task"]
        task_id = task["task_id"]
        summary["task_added"] = task

        start_response = send_command(
            automation_dir,
            "start_task",
            {"task_id": task_id},
            timeout_seconds=args.command_timeout,
        )
        if not start_response.get("ok"):
            raise RuntimeError(start_response.get("error") or "start_task failed")
        summary["start_result"] = start_response["data"]
        summary["running_task"] = wait_for_task_status(automation_dir, task_id, {"pending", "running"}, timeout_seconds=20)

        variants = [
            {"name": "record_limit", "payload": {"source": "record", "limit": args.log_limit}},
            {"name": "all_limit", "payload": {"limit": args.log_limit}},
            {"name": "keyword_task", "payload": {"keyword": "任务", "limit": 30}},
            {"name": "automation_limit", "payload": {"source": "automation", "limit": 20}},
        ]
        summary["get_logs_stability"] = query_get_logs(
            automation_dir,
            variants=variants,
            timeout_seconds=args.query_timeout,
            duration_seconds=args.record_seconds,
            interval_seconds=args.query_interval,
        )

        stop_response = send_command(
            automation_dir,
            "stop_task",
            {"task_id": task_id},
            timeout_seconds=args.command_timeout,
        )
        if not stop_response.get("ok"):
            raise RuntimeError(stop_response.get("error") or "stop_task failed")
        summary["stop_result"] = stop_response["data"]
        summary["stopped_task"] = wait_for_task_status(
            automation_dir,
            task_id,
            {"stopped", "completed", "failed"},
            timeout_seconds=20,
        )
        summary["history_record"] = wait_for_history(automation_dir, task_id, timeout_seconds=20)
        final_logs = send_command(
            automation_dir,
            "get_logs",
            {"source": "record", "limit": args.log_limit},
            timeout_seconds=args.command_timeout,
        )
        summary["final_get_logs"] = final_logs.get("data") if final_logs.get("ok") else {"error": final_logs.get("error")}
        stability = summary["get_logs_stability"]
        if not isinstance(stability, dict):
            raise RuntimeError("missing get_logs stability summary")
        summary["success"] = stability.get("failed_calls", 1) == 0
    finally:
        try:
            send_command(automation_dir, "shutdown", {}, timeout_seconds=5)
        except Exception:
            pass
        if client_process is not None:
            try:
                client_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                client_process.kill()
                client_process.wait(timeout=5)
            summary["client_exit_code"] = client_process.returncode
        stop_process(source_process)
        summary["source_exit_code"] = None if source_process is None else source_process.returncode
        (workspace / "acceptance_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
