from __future__ import annotations

import argparse
import asyncio
import logging
import os
import random
import re
import shutil
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from src import spider, stream

from .config import ConfigError, QUALITY_ALIASES, load_config, redact_secret
from .health import HealthState
from .identity_cache import IdentityCache, resolved_identity
from .models import AppConfig, RoomConfig
from .observations import ObservationStore, classify_check_failure
from .postprocess import PostProcessQueue
from .process_manager import ProcessManager, build_ffmpeg_command

LOGGER = logging.getLogger("douyin-daemon")


def retry_delay(attempt: int, *, base: float = 5.0, maximum: float = 300.0, jitter: float = 0.2) -> float:
    delay = min(maximum, base * (2 ** max(0, attempt)))
    return delay * (1 + random.uniform(-jitter, jitter))


def _safe_name(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    return cleaned[:100] or "douyin"


def _redact_error(value: str) -> str:
    sanitized = re.sub(r"(https?://[^\s?]+)\?[^\s]+", r"\1?<redacted>", value)
    sanitized = re.sub(
        r"(?i)\b(cookie|authorization|token|password)\s*[:=]\s*\S+",
        r"\1=<redacted>",
        sanitized,
    )
    return sanitized[-1000:]


def select_stream_url(result: dict[str, Any], protocol: str) -> str:
    flv_url = str(result.get("flv_url") or "")
    hls_url = str(result.get("m3u8_url") or "")
    if protocol == "flv":
        return flv_url or hls_url
    if protocol == "hls":
        return hls_url or flv_url
    codec_hint = f"{flv_url} {hls_url}".lower()
    if "h265" in codec_hint or "hevc" in codec_hint:
        return hls_url or flv_url
    return flv_url or hls_url


def classify_recording_end(
    return_code: int,
    error_text: str,
    *,
    stopping: bool,
    disk_available: bool,
) -> str:
    text = error_text.lower()
    if stopping:
        return "user_stop"
    if not disk_available or "no space left" in text:
        return "disk_space_low"
    if return_code == 0:
        return "stream_ended"
    if "401" in text or "403" in text or "cookie" in text:
        return "cookie_invalid"
    if any(word in text for word in ("captcha", "risk", "verify", "412 precondition")):
        return "risk_control"
    if any(
        word in text
        for word in ("timed out", "connection reset", "connection refused", "network is unreachable")
    ):
        return "network_disconnect"
    return "ffmpeg_crash"


class DouyinDaemon:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.shutdown_event = threading.Event()
        self.processes = ProcessManager()
        self.health = HealthState(config.storage.state_path)
        self.identities = IdentityCache(config.storage.state_path)
        self.observations = ObservationStore(config.storage.state_path)
        self.pool = ThreadPoolExecutor(
            max_workers=config.recorder.max_concurrent_checks,
            thread_name_prefix="douyin-check",
        )
        self.record_threads: dict[str, threading.Thread] = {}
        self._lock = threading.RLock()
        self._ffmpeg_crashes = 0
        self.postprocess = PostProcessQueue(
            self.processes,
            workers=config.recorder.remux_workers,
            delete_source=config.recorder.delete_source_after_remux,
            stopping=self.shutdown_event,
        )

    def request_shutdown(self, signum: int | None = None) -> None:
        if not self.shutdown_event.is_set():
            LOGGER.info("shutdown_requested signal=%s", signum)
            self.shutdown_event.set()
            self.health.update(stopping=True, heartbeat_at=time.time())
            threading.Thread(
                target=self.processes.stop_all,
                name="ffmpeg-shutdown",
                daemon=True,
            ).start()

    def _disk_available(self) -> bool:
        free_gb = shutil.disk_usage(self.config.storage.path).free / (1024**3)
        if free_gb < self.config.storage.min_free_gb:
            LOGGER.error(
                "disk_space_low free_gb=%.2f required_gb=%.2f",
                free_gb,
                self.config.storage.min_free_gb,
            )
            return False
        return True

    def _resolve(self, room: RoomConfig) -> tuple[RoomConfig, dict[str, Any]]:
        async def resolve() -> dict[str, Any]:
            resolver = (
                spider.get_douyin_app_stream_data
                if "v.douyin.com" in room.url or "/user/" in room.url
                else spider.get_douyin_web_stream_data
            )
            data = await resolver(
                room.url,
                proxy_addr=self.config.proxy.url or None,
                cookies=self.config.cookie or None,
            )
            result = await stream.get_douyin_stream_url(
                data,
                QUALITY_ALIASES[room.quality],
                self.config.proxy.url or None,
            )
            result["room_id"] = data.get("id_str") or data.get("id") or data.get("room_id")
            result["web_rid"] = data.get("web_rid")
            identity = resolved_identity(data, result)
            if identity:
                result["_identity"] = identity
                self.identities.remember(room.url, identity)
            return result

        return room, asyncio.run(resolve())

    def _record(self, key: str, room: RoomConfig, result: dict[str, Any]) -> None:
        stream_url = select_stream_url(result, self.config.recorder.stream_protocol)
        if not stream_url or self.shutdown_event.is_set() or not self._disk_available():
            return
        anchor = _safe_name(room.name or str(result.get("anchor_name") or key))
        output_dir = self.config.storage.path / anchor
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output = output_dir / f"{anchor}_{stamp}_%03d.ts"
        command = build_ffmpeg_command(
            stream_url,
            output,
            segment_seconds=self.config.recorder.segment_seconds,
            proxy_url=self.config.proxy.url,
        )
        try:
            managed = self.processes.start(key, command)
            LOGGER.info("recording_started room=%s anchor=%s", key, anchor)
            return_code = self.processes.wait(key)
            reason = classify_recording_end(
                return_code,
                "\n".join(managed.errors),
                stopping=self.shutdown_event.is_set(),
                disk_available=self._disk_available(),
            )
            if reason == "ffmpeg_crash":
                self._ffmpeg_crashes += 1
            self.health.update(
                last_ffmpeg_return_code=return_code,
                last_ffmpeg_error=_redact_error(managed.errors[-1] if managed.errors else ""),
                ffmpeg_crashes=self._ffmpeg_crashes,
            )
            LOGGER.info("recording_stopped room=%s code=%s reason=%s", key, return_code, reason)
            if (
                self.config.recorder.remux_to_mp4
                and not self.shutdown_event.is_set()
                and reason == "stream_ended"
            ):
                for source in sorted(output_dir.glob(f"{anchor}_{stamp}_*.ts")):
                    self.postprocess.submit(source)
        except Exception:
            self._ffmpeg_crashes += 1
            LOGGER.exception("recording_failed room=%s", key)
        finally:
            with self._lock:
                self.record_threads.pop(key, None)

    @staticmethod
    def _room_key(room: RoomConfig, result: dict[str, Any]) -> str:
        identity = result.get("_identity")
        if identity:
            return str(identity)
        room_id = result.get("room_id") or result.get("web_rid")
        anchor = result.get("anchor_name")
        return str(room_id or anchor or room.url)

    def _handle_check_result(self, room: RoomConfig, result: dict[str, Any]) -> None:
        if self.shutdown_event.is_set():
            return
        key = self._room_key(room, result)
        if not result.get("is_live"):
            LOGGER.info("room_offline room=%s", key)
            return
        with self._lock:
            if key in self.record_threads or key in self.processes.active_keys():
                return
            thread = threading.Thread(
                target=self._record,
                args=(key, room, result),
                name=f"record-{_safe_name(key)}",
            )
            self.record_threads[key] = thread
            thread.start()

    def run(self) -> int:
        LOGGER.info(
            "daemon_started rooms=%d poll_seconds=%d cookie=%s",
            len(self.config.rooms),
            self.config.recorder.poll_seconds,
            redact_secret(self.config.cookie),
        )
        if not self.config.cookie:
            LOGGER.warning("douyin_cookie_missing some rooms or qualities may be unavailable")
        self.health.update(heartbeat_at=time.time(), last_check_at=time.time(), stopping=False)
        failures = 0
        while not self.shutdown_event.is_set():
            if not self._disk_available():
                self.request_shutdown()
                break
            rooms = self.identities.deduplicate(self.config.rooms)
            futures = [self.pool.submit(self._resolve, room) for room in rooms]
            completed = 0
            for future in futures:
                if self.shutdown_event.is_set():
                    break
                try:
                    room, result = future.result(timeout=45)
                    self._handle_check_result(room, result)
                    completed += 1
                except Exception as exc:
                    failures += 1
                    category = classify_check_failure(str(exc))
                    fingerprint = self.observations.record(category, exc)
                    LOGGER.error(
                        "room_check_failed category=%s error_type=%s fingerprint=%s",
                        category,
                        type(exc).__name__,
                        fingerprint,
                    )
            now = time.time()
            self.health.update(
                heartbeat_at=now,
                last_check_at=now if completed else self.health.state["last_check_at"],
                check_failures=failures,
                check_failure_categories=self.observations.counters,
                ffmpeg_crashes=self._ffmpeg_crashes,
                active_recordings=len(self.processes.active_keys()),
            )
            delay = self.config.recorder.poll_seconds if completed else retry_delay(min(failures, 6))
            self.shutdown_event.wait(delay)
        self.pool.shutdown(wait=True, cancel_futures=True)
        self.processes.stop_all()
        for thread in list(self.record_threads.values()):
            thread.join(timeout=60)
        self.postprocess.shutdown(wait=True)
        self.health.update(
            heartbeat_at=time.time(),
            active_recordings=0,
            stopping=True,
        )
        LOGGER.info("daemon_stopped")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unattended Douyin recording daemon")
    parser.add_argument(
        "--config",
        default=os.environ.get("DOUYIN_CONFIG", "/app/config/douyin.yaml"),
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s level=%(levelname)s logger=%(name)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        LOGGER.error("configuration_invalid error=%s", exc)
        return 2
    daemon = DouyinDaemon(config)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda signum, _frame, service=daemon: service.request_shutdown(signum))
    return daemon.run()


if __name__ == "__main__":
    sys.exit(main())
