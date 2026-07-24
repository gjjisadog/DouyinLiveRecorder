"""Run packaged EXE acceptance through the file-based automation bridge."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

AUTOMATION_ENV = "DLR_AUTOMATION_DIR"
DEFAULT_STREAM_URL = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"


def write_json_atomically(path: Path, payload: dict) -> None:
    temp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run packaged client acceptance via automation bridge.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--exe-path", type=Path, default=None)
    parser.add_argument("--stream-url", default=DEFAULT_STREAM_URL)
    parser.add_argument("--display-name", default="BL002_EXE_Automation")
    parser.add_argument("--record-seconds", type=int, default=8)
    parser.add_argument("--max-file-size-gb", type=float, default=1.0)
    parser.add_argument("--split-seconds", type=int, default=1800)
    parser.add_argument("--loop-seconds", type=int, default=300)
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--log-limit", type=int, default=50)
    parser.add_argument("--startup-timeout", type=int, default=30)
    parser.add_argument("--command-timeout", type=int, default=20)
    return parser.parse_args()


def detect_ffmpeg_dir() -> Path:
    candidates = [
        Path(os.environ.get("FFMPEG_DIR", "")),
        Path(
            r"C:\Users\wxw\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-essentials_build\bin"
        ),
    ]
    for candidate in candidates:
        if candidate and candidate.exists() and (candidate / "ffmpeg.exe").exists():
            return candidate
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return Path(ffmpeg_path).resolve().parent
    raise FileNotFoundError("ffmpeg.exe not found. Install ffmpeg or set FFMPEG_DIR first.")


def prepare_workspace(workspace: Path, *, max_file_size_gb: float, split_seconds: int, loop_seconds: int) -> None:
    if workspace.exists():
        shutil.rmtree(workspace)
    client_data = workspace / "client_data"
    client_data.mkdir(parents=True, exist_ok=True)
    config = {
        "version": 1,
        "config": {
            "output_dir": str(workspace / "downloads"),
            "output_format": "ts",
            "quality": "原画",
            "max_file_size_gb": max_file_size_gb,
            "max_concurrency": 3,
            "loop_seconds": loop_seconds,
            "queue_seconds": 0,
            "split_recording": True,
            "split_seconds": split_seconds,
            "use_proxy": False,
            "proxy_url": "",
            "use_https_recording": False,
            "folder_by_author": True,
            "folder_by_time": False,
            "folder_by_title": False,
            "filename_include_title": False,
            "clean_emoji": True,
            "disk_space_limit_gb": 1.0,
            "convert_to_mp4": False,
            "convert_to_h264": False,
            "delete_origin_after_convert": True,
            "create_time_file": False,
            "show_source_url": False,
            "disable_record": False,
            "custom_script": "",
            "enable_notifications": False,
            "notify_channels": "",
            "douyin_cookie": "",
            "push_settings": {},
            "cookies": {},
            "authorization": {},
            "credentials": {},
            "proxy_platforms": [],
            "extra_proxy_platforms": [],
            "minimize_to_tray": False,
            "close_to_tray": False,
            "start_on_boot": False,
            "restore_tasks_on_launch": False,
            "restore_window_on_launch": False,
        },
    }
    runtime_state = {
        "version": 1,
        "last_exit_clean": True,
        "running_task_ids": [],
        "scheduler_running": True,
        "current_tab_index": 0,
        "hidden_to_tray": False,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (client_data / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    (client_data / "runtime_state.json").write_text(json.dumps(runtime_state, ensure_ascii=False, indent=2), encoding="utf-8")
    (client_data / "tasks.json").write_text(json.dumps({"version": 1, "tasks": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    (client_data / "history.json").write_text("[]", encoding="utf-8")


def send_command(automation_dir: Path, command: str, payload: dict, timeout_seconds: int) -> dict:
    request_id = uuid.uuid4().hex
    request_path = automation_dir / "request.json"
    response_path = automation_dir / "response.json"
    write_json_atomically(request_path, {"id": request_id, "command": command, "payload": payload})
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if response_path.exists():
            try:
                raw_response = response_path.read_text(encoding="utf-8")
            except OSError:
                time.sleep(0.05)
                continue
            if not raw_response.strip():
                time.sleep(0.05)
                continue
            try:
                response = json.loads(raw_response)
            except json.JSONDecodeError:
                time.sleep(0.05)
                continue
            if response.get("request_id") == request_id:
                return response
        time.sleep(0.2)
    raise TimeoutError(f"Timed out waiting for automation response: {command}")


def wait_for_task_status(automation_dir: Path, task_id: str, statuses: set[str], timeout_seconds: int) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        response = send_command(automation_dir, "list_tasks", {}, timeout_seconds=10)
        if not response.get("ok"):
            raise RuntimeError(response.get("error") or "list_tasks failed")
        tasks = response["data"]["tasks"]
        for task in tasks:
            if task["task_id"] == task_id and task["status"] in statuses:
                return task
        time.sleep(0.5)
    raise TimeoutError(f"Task {task_id} did not reach {sorted(statuses)} within {timeout_seconds}s")


def wait_for_history(automation_dir: Path, task_id: str, timeout_seconds: int) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        response = send_command(automation_dir, "list_history", {}, timeout_seconds=10)
        if not response.get("ok"):
            raise RuntimeError(response.get("error") or "list_history failed")
        for record in response["data"]["records"]:
            if record["task_id"] == task_id:
                return record
        time.sleep(0.5)
    raise TimeoutError(f"History record did not appear within {timeout_seconds}s: {task_id}")


def resolve_output_files(output_pattern: str | None) -> list[Path]:
    if not output_pattern:
        return []
    pattern_path = Path(output_pattern)
    if "%03d" in pattern_path.name:
        return sorted(path for path in pattern_path.parent.glob(pattern_path.name.replace("%03d", "*")) if path.is_file())
    if pattern_path.exists():
        return [pattern_path]
    return []


def wait_for_output_files(output_pattern: str | None, timeout_seconds: int) -> list[Path]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        output_files = resolve_output_files(output_pattern)
        if output_files:
            return output_files
        time.sleep(0.5)
    raise TimeoutError(f"Recording output did not appear within {timeout_seconds}s: {output_pattern}")


def observe_recording(
    automation_dir: Path,
    *,
    task_id: str,
    record_seconds: int,
    poll_interval: float,
    command_timeout: int,
) -> dict[str, object]:
    deadline = time.time() + record_seconds
    task_snapshots: list[dict[str, object]] = []
    history_counts: list[dict[str, object]] = []
    output_patterns: list[str] = []

    while time.time() < deadline:
        elapsed_seconds = round(record_seconds - max(deadline - time.time(), 0), 2)

        list_response = send_command(automation_dir, "list_tasks", {}, timeout_seconds=command_timeout)
        if not list_response.get("ok"):
            raise RuntimeError(list_response.get("error") or "list_tasks failed during observation")
        task = next((item for item in list_response["data"]["tasks"] if item["task_id"] == task_id), None)
        if task is not None:
            output_path = task.get("output_path")
            if output_path:
                output_patterns.append(str(output_path))
            task_snapshots.append(
                {
                    "elapsed_seconds": elapsed_seconds,
                    "status": task.get("status"),
                    "output_path": output_path,
                    "last_error": task.get("last_error"),
                }
            )

        history_response = send_command(automation_dir, "list_history", {}, timeout_seconds=command_timeout)
        if not history_response.get("ok"):
            raise RuntimeError(history_response.get("error") or "list_history failed during observation")
        record_count = sum(1 for record in history_response["data"]["records"] if record["task_id"] == task_id)
        history_counts.append({"elapsed_seconds": elapsed_seconds, "count": record_count})

        sleep_seconds = min(poll_interval, max(deadline - time.time(), 0))
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    return {
        "task_snapshots": task_snapshots,
        "history_counts": history_counts,
        "unique_output_patterns": sorted({pattern for pattern in output_patterns if pattern}),
    }


def collect_workspace_output_files(workspace: Path, output_format: str = "ts") -> list[Path]:
    output_root = workspace / "downloads"
    if not output_root.exists():
        return []
    return sorted(path for path in output_root.rglob(f"*.{output_format}") if path.is_file())


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    workspace = (args.workspace or (repo_root / "tmp_bl002_exe_automation")).resolve()
    exe_path = (args.exe_path or (repo_root / "dist" / "DouyinLiveRecorder Client" / "DouyinLiveRecorder Client.exe")).resolve()
    automation_dir = workspace / "client_data" / "automation"
    prepare_workspace(
        workspace,
        max_file_size_gb=args.max_file_size_gb,
        split_seconds=args.split_seconds,
        loop_seconds=args.loop_seconds,
    )
    automation_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg_dir = detect_ffmpeg_dir()
    env = os.environ.copy()
    env["PATH"] = str(ffmpeg_dir) + os.pathsep + env.get("PATH", "")
    env[AUTOMATION_ENV] = str(automation_dir)

    subprocess.run(["taskkill", "/IM", "DouyinLiveRecorder Client.exe", "/F"], capture_output=True)
    process = subprocess.Popen([str(exe_path)], cwd=str(workspace), env=env)
    summary: dict[str, object] = {
        "workspace": str(workspace),
        "automation_dir": str(automation_dir),
        "exe_path": str(exe_path),
        "ffmpeg_dir": str(ffmpeg_dir),
        "process_id": process.pid,
        "record_seconds": args.record_seconds,
        "max_file_size_gb": args.max_file_size_gb,
        "split_seconds": args.split_seconds,
        "loop_seconds": args.loop_seconds,
        "poll_interval": args.poll_interval,
    }

    try:
        send_command(automation_dir, "ping", {}, timeout_seconds=args.startup_timeout)
        add_response = send_command(
            automation_dir,
            "add_task",
            {
                "url": args.stream_url,
                "display_name": args.display_name,
                "quality": "原画",
                "enabled": True,
            },
            timeout_seconds=args.command_timeout,
        )
        if not add_response.get("ok"):
            raise RuntimeError(add_response.get("error") or "add_task failed")
        add_data = add_response["data"]
        task = add_data["task"]
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
        summary["observation"] = observe_recording(
            automation_dir,
            task_id=task_id,
            record_seconds=args.record_seconds,
            poll_interval=args.poll_interval,
            command_timeout=args.command_timeout,
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

        history_response = send_command(automation_dir, "list_history", {}, timeout_seconds=args.command_timeout)
        if not history_response.get("ok"):
            raise RuntimeError(history_response.get("error") or "list_history failed after stop")
        history_records = [record for record in history_response["data"]["records"] if record["task_id"] == task_id]
        summary["history_records"] = history_records

        try:
            logs_response = send_command(
                automation_dir,
                "get_logs",
                {"source": "record", "limit": args.log_limit},
                timeout_seconds=args.command_timeout,
            )
            if logs_response.get("ok"):
                record_logs = logs_response["data"]["entries"]
                summary["record_logs"] = record_logs
            else:
                record_logs = []
                summary["record_logs_error"] = logs_response.get("error")
        except Exception as exc:
            record_logs = []
            summary["record_logs_error"] = str(exc)

        output_pattern = summary["running_task"].get("output_path")
        output_files = wait_for_output_files(output_pattern, timeout_seconds=10)
        summary["output_pattern"] = output_pattern
        summary["output_files"] = [{"path": str(path), "size": path.stat().st_size} for path in output_files]

        all_output_files = collect_workspace_output_files(workspace)
        all_output_file_items = [{"path": str(path), "size": path.stat().st_size} for path in all_output_files]
        summary["all_output_files"] = all_output_file_items

        threshold_bytes = max(int(args.max_file_size_gb * 1024 * 1024 * 1024), 1) if args.max_file_size_gb > 0 else None
        summary["threshold_bytes"] = threshold_bytes
        if threshold_bytes is not None and all_output_file_items:
            overshoot_items = [
                {
                    "path": item["path"],
                    "size": item["size"],
                    "overshoot_bytes": max(int(item["size"]) - threshold_bytes, 0),
                }
                for item in all_output_file_items
            ]
            summary["overshoot"] = {
                "files": overshoot_items,
                "max_overshoot_bytes": max(item["overshoot_bytes"] for item in overshoot_items),
            }

        observation = summary["observation"]
        unique_output_patterns = observation["unique_output_patterns"] if isinstance(observation, dict) else []
        summary["rollover_detected"] = (
            len(unique_output_patterns) >= 2
            or len(history_records) >= 2
            or any("单文件上限" in str(entry.get("message") or "") for entry in record_logs)
        )
        if not summary["history_record"].get("file_path"):
            raise RuntimeError("history record missing file_path")

        summary["success"] = True
    finally:
        try:
            send_command(automation_dir, "shutdown", {}, timeout_seconds=5)
        except Exception:
            pass
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        summary["exit_code"] = process.returncode
        (workspace / "acceptance_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
