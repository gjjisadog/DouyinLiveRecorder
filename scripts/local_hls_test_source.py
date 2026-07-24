"""Run a local long-lived HLS test source for recorder acceptance."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local HLS source for acceptance testing.")
    parser.add_argument("--workspace", type=Path, default=Path("tmp_local_hls_source"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--video-bitrate-mbps", type=int, default=24)
    parser.add_argument("--audio-bitrate-kbps", type=int, default=192)
    parser.add_argument("--segment-seconds", type=int, default=2)
    parser.add_argument("--playlist-size", type=int, default=12)
    parser.add_argument("--ffmpeg-path", type=Path, default=None)
    parser.add_argument("--startup-timeout", type=int, default=30)
    parser.add_argument("--keep-workspace", action="store_true")
    return parser.parse_args()


def detect_ffmpeg_path(explicit_path: Path | None) -> Path:
    candidates = [
        explicit_path,
        Path(os.environ.get("FFMPEG_DIR", "")) / "ffmpeg.exe",
        Path(
            r"C:\Users\wxw\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe"
        ),
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return Path(ffmpeg_path).resolve()
    raise FileNotFoundError("ffmpeg.exe not found. Install ffmpeg or pass --ffmpeg-path.")


def build_ffmpeg_command(args: argparse.Namespace, ffmpeg_path: Path, playlist_path: Path) -> list[str]:
    video_bitrate = f"{args.video_bitrate_mbps}M"
    audio_bitrate = f"{args.audio_bitrate_kbps}k"
    segment_pattern = playlist_path.parent / "segment_%06d.ts"
    return [
        str(ffmpeg_path),
        "-hide_banner",
        "-loglevel",
        "warning",
        "-re",
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=size={args.width}x{args.height}:rate={args.fps}",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=1000:sample_rate=48000",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "mpeg2video",
        "-pix_fmt",
        "yuv420p",
        "-b:v",
        video_bitrate,
        "-minrate",
        video_bitrate,
        "-maxrate",
        video_bitrate,
        "-bufsize",
        f"{args.video_bitrate_mbps * 2}M",
        "-g",
        str(max(args.fps, 1)),
        "-bf",
        "2",
        "-c:a",
        "mp2",
        "-b:a",
        audio_bitrate,
        "-f",
        "hls",
        "-hls_time",
        str(args.segment_seconds),
        "-hls_list_size",
        str(args.playlist_size),
        "-hls_flags",
        "delete_segments+append_list+omit_endlist+independent_segments",
        "-hls_segment_filename",
        str(segment_pattern),
        str(playlist_path),
    ]


def wait_for_playlist(playlist_path: Path, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if playlist_path.exists() and playlist_path.stat().st_size > 0:
            return
        time.sleep(0.2)
    raise TimeoutError(f"Timed out waiting for playlist: {playlist_path}")


def run() -> int:
    args = parse_args()
    workspace = args.workspace.resolve()
    hls_dir = workspace / "hls"
    playlist_path = hls_dir / "stream.m3u8"

    if workspace.exists() and not args.keep_workspace:
        shutil.rmtree(workspace)
    hls_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg_path = detect_ffmpeg_path(args.ffmpeg_path)
    command = build_ffmpeg_command(args, ffmpeg_path, playlist_path)
    info = {
        "workspace": str(workspace),
        "playlist_path": str(playlist_path),
        "stream_url": f"http://{args.host}:{args.port}/stream.m3u8",
        "ffmpeg_path": str(ffmpeg_path),
        "command": command,
    }
    (workspace / "source_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    handler = partial(SimpleHTTPRequestHandler, directory=str(hls_dir))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    process = subprocess.Popen(command, cwd=str(workspace))
    stop_event = threading.Event()

    def shutdown(*_args) -> None:
        if stop_event.is_set():
            return
        stop_event.set()
        try:
            server.shutdown()
        except Exception:
            pass
        try:
            server.server_close()
        except Exception:
            pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        wait_for_playlist(playlist_path, args.startup_timeout)
        print(json.dumps(info, ensure_ascii=False, indent=2))
        while not stop_event.is_set():
            if process.poll() is not None:
                raise RuntimeError(f"ffmpeg source process exited unexpectedly: {process.returncode}")
            time.sleep(1)
        return 0
    finally:
        shutdown()


if __name__ == "__main__":
    raise SystemExit(run())
