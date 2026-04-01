"""FFmpeg process service."""

from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from client.core.enums import OutputFormat, Platform
from client.core.models import AppConfig, RecordSession, RecordTask, StreamInfo
from client.infra.logging.log_service import LEVEL_DEBUG, LEVEL_INFO, LogEmitterMixin, SOURCE_RECORD

INVALID_FILENAME_PATTERN = r"[\/\\\:\*\?\"\<\>\|&# ]"
WINDOWS = os.name == "nt"
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002702-\U000027B0"
    "]+",
    flags=re.UNICODE,
)


class FfmpegService(LogEmitterMixin):
    def __init__(self) -> None:
        super().__init__(log_source=SOURCE_RECORD)
        self._processes: dict[str, subprocess.Popen] = {}

    def build_command(self, task: RecordTask, stream: StreamInfo, config: AppConfig) -> tuple[list[str], Path]:
        record_url = self.select_source_url(task, stream)
        if not record_url:
            raise RuntimeError("No recordable stream URL was produced.")

        output_file = self.build_output_path(task, stream, config)
        self._emit_log(
            f"已为任务 {task.task_id} 生成输出路径：{output_file}",
            LEVEL_DEBUG,
        )
        command = [
            "ffmpeg",
            "-y",
            "-v",
            "verbose",
            "-rw_timeout",
            "15000000",
            "-loglevel",
            "error",
            "-hide_banner",
            "-user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "-protocol_whitelist",
            "rtmp,crypto,file,http,https,tcp,tls,udp,rtp,httpproxy",
            "-thread_queue_size",
            "1024",
            "-analyzeduration",
            "20000000",
            "-probesize",
            "10000000",
            "-fflags",
            "+discardcorrupt",
            "-re",
            "-i",
            record_url,
            "-bufsize",
            "8000k",
            "-sn",
            "-dn",
            "-reconnect_delay_max",
            "60",
            "-reconnect_streamed",
            "-reconnect_at_eof",
            "-max_muxing_queue_size",
            "1024",
            "-correct_ts_overflow",
            "1",
            "-avoid_negative_ts",
            "1",
        ]

        headers = self.get_record_headers(task.platform, task.url)
        if headers:
            command[10:10] = ["-headers", headers]

        proxy_address = self._select_proxy(task.url, config)
        if proxy_address:
            command[1:1] = ["-http_proxy", proxy_address]
            self._emit_log(f"任务 {task.task_id} 将通过代理发起录制。", LEVEL_DEBUG)

        if config.use_https_recording and record_url.startswith("http://"):
            command[command.index(record_url)] = record_url.replace("http://", "https://", 1)
            self._emit_log(f"任务 {task.task_id} 已切换为 HTTPS 录制源。", LEVEL_DEBUG)

        command.extend(self._build_output_args(config.output_format, output_file, config))
        self._emit_log(
            f"已为任务 {task.task_id} 生成 ffmpeg 命令，输出格式 {config.output_format.value}。",
            LEVEL_DEBUG,
        )
        return command, output_file

    def start_record(self, task: RecordTask, command: list[str], output_file: Path) -> RecordSession:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            startupinfo=self._get_startup_info(),
        )
        self._processes[task.task_id] = process
        self._emit_log(
            f"任务 {task.task_id} 的 ffmpeg 进程已启动，PID={process.pid}。",
            LEVEL_INFO,
        )
        return RecordSession(
            task_id=task.task_id,
            started_at=datetime.now(),
            process_id=process.pid,
            output_file=output_file,
            command=command,
        )

    def stop_record(self, task: RecordTask) -> None:
        process = self._processes.pop(task.task_id, None)
        if process is None:
            self._emit_log(f"任务 {task.task_id} 当前没有活动的 ffmpeg 进程。", LEVEL_DEBUG)
            return

        try:
            if WINDOWS and process.stdin:
                process.stdin.write(b"q")
                process.stdin.close()
            else:
                process.terminate()
            process.wait(timeout=10)
            self._emit_log(f"任务 {task.task_id} 的 ffmpeg 进程已正常结束。", LEVEL_INFO)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            self._emit_log(f"任务 {task.task_id} 的 ffmpeg 进程超时，已强制结束。", LEVEL_INFO)

    def poll_record(self, task_id: str) -> int | None:
        process = self._processes.get(task_id)
        if process is None:
            return 0

        return_code = process.poll()
        if return_code is None:
            return None

        self._processes.pop(task_id, None)
        return return_code

    def is_recording(self, task_id: str) -> bool:
        return self.poll_record(task_id) is None

    def build_output_path(self, task: RecordTask, stream: StreamInfo, config: AppConfig) -> Path:
        anchor_name = self.clean_name(task.display_name or task.anchor_name or task.task_id, config.clean_emoji)
        title_name = self.clean_name(stream.title or task.title or "", config.clean_emoji)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        output_dir = Path(config.output_dir)
        if config.folder_by_author:
            output_dir /= anchor_name
        if config.folder_by_time:
            output_dir /= datetime.now().strftime("%Y-%m-%d")
        if config.folder_by_title and title_name:
            output_dir /= title_name

        filename_parts = [anchor_name]
        if config.filename_include_title and title_name:
            filename_parts.append(title_name)
        filename_parts.append(timestamp)

        filename = "_".join(part for part in filename_parts if part)
        if config.split_recording:
            filename += "_%03d"
        return output_dir / f"{filename}.{config.output_format.value}"

    def select_source_url(self, task: RecordTask, stream: StreamInfo) -> str:
        if self.is_flv_preferred_platform(task) and stream.flv_url:
            codec = self._get_query_params(stream.flv_url, "codec")
            if not codec or codec[0] != "h265":
                return stream.flv_url
        return stream.record_url or stream.m3u8_url or stream.flv_url

    def clean_name(self, value: str, clean_emoji: bool) -> str:
        cleaned = re.sub(INVALID_FILENAME_PATTERN, "_", value.strip()).strip("_")
        if clean_emoji:
            cleaned = EMOJI_PATTERN.sub("_", cleaned).strip("_")
        return cleaned or "unnamed"

    def get_record_headers(self, platform: Platform, live_url: str) -> str | None:
        live_domain = "/".join(live_url.split("/")[0:3])
        if "pandalive" in live_url:
            return "origin:https://www.pandalive.co.kr"
        if "winktv" in live_url:
            return "origin:https://www.winktv.co.kr"
        if "popkontv" in live_url:
            return "origin:https://www.popkontv.com"
        if "flextv" in live_url or "ttinglive" in live_url:
            return "origin:https://www.flextv.co.kr"
        if "shopee" in live_url or ".shp.ee" in live_url:
            return f"origin:{live_domain}"
        if "blued" in live_url:
            return "referer:https://app.blued.cn"
        _ = platform
        return None

    def is_flv_preferred_platform(self, task: RecordTask) -> bool:
        return task.platform in {Platform.DOUYIN, Platform.TIKTOK}

    def _select_proxy(self, url: str, config: AppConfig) -> str | None:
        if not config.use_proxy or not config.proxy_url:
            return None

        lower_url = url.lower()
        if not config.proxy_platforms and not config.extra_proxy_platforms:
            return config.proxy_url
        if any(platform in lower_url for platform in config.proxy_platforms):
            return config.proxy_url
        if any(platform in lower_url for platform in config.extra_proxy_platforms):
            return config.proxy_url
        return None

    def _build_output_args(self, output_format: OutputFormat, output_file: Path, config: AppConfig) -> list[str]:
        split_args: list[str] = []
        if config.split_recording:
            split_args = ["-f", "segment", "-segment_time", str(config.split_seconds), "-reset_timestamps", "1"]

        if output_format == OutputFormat.FLV:
            args = ["-map", "0", "-c:v", "copy", "-c:a", "copy", "-bsf:a", "aac_adtstoasc"]
            if config.split_recording:
                args.extend(split_args + ["-segment_format", "flv"])
            else:
                args.extend(["-f", "flv"])
            return args + [str(output_file)]

        if output_format == OutputFormat.MKV:
            args = ["-flags", "global_header", "-map", "0", "-c:v", "copy", "-c:a", "copy"]
            if config.split_recording:
                args.extend(split_args + ["-segment_format", "matroska"])
            else:
                args.extend(["-f", "matroska"])
            return args + [str(output_file)]

        if output_format == OutputFormat.MP4:
            args = ["-map", "0", "-c:v", "copy", "-c:a", "copy"]
            if config.split_recording:
                args.extend(split_args + ["-segment_format", "mp4", "-movflags", "+frag_keyframe+empty_moov"])
            else:
                args.extend(["-f", "mp4"])
            return args + [str(output_file)]

        if output_format == OutputFormat.MP3:
            return ["-map", "0:a", "-c:a", "libmp3lame", "-ab", "320k"] + split_args + [str(output_file)]

        if output_format == OutputFormat.M4A:
            args = ["-map", "0:a", "-c:a", "aac", "-bsf:a", "aac_adtstoasc", "-ab", "320k"]
            if config.split_recording:
                args.extend(split_args + ["-segment_format", "mpegts"])
            else:
                args.extend(["-movflags", "+faststart"])
            return args + [str(output_file)]

        args = ["-c:v", "copy", "-c:a", "copy", "-map", "0"]
        if config.split_recording:
            args.extend(split_args + ["-segment_format", "mpegts"])
        else:
            args.extend(["-f", "mpegts"])
        return args + [str(output_file)]

    def _get_startup_info(self) -> subprocess.STARTUPINFO | None:
        if not WINDOWS:
            return None
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return startup_info

    def _get_query_params(self, url: str, param_name: str) -> list[str]:
        query_params = parse_qs(urlparse(url).query)
        return query_params.get(param_name, [])
