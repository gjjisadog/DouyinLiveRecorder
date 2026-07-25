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

import yaml

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
    def __init__(self, config: AppConfig, config_path: Path | None = None) -> None:
        self.config = config
        self.config_path = config_path
        self.shutdown_event = threading.Event()
        self._wake_event = threading.Event()
        self.processes = ProcessManager()
        self.health = HealthState(config.storage.state_path)
        self.identities = IdentityCache(config.storage.state_path)
        self.observations = ObservationStore(config.storage.state_path)
        self.pool = ThreadPoolExecutor(
            max_workers=config.recorder.max_concurrent_checks,
            thread_name_prefix="douyin-check",
        )
        self.record_threads: dict[str, threading.Thread] = {}
        self.recording_room_urls: dict[str, str] = {}
        self._lock = threading.RLock()
        self._config_fingerprint = self._fingerprint_config()
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
            self._wake_event.set()
            self.health.update(stopping=True, heartbeat_at=time.time())
            threading.Thread(
                target=self.processes.stop_all,
                name="ffmpeg-shutdown",
                daemon=True,
            ).start()

    def _current_config(self) -> AppConfig:
        with self._lock:
            return self.config

    def _fingerprint_config(self) -> tuple[int, int] | None:
        if self.config_path is None:
            return None
        try:
            stat = self.config_path.stat()
        except OSError:
            return None
        return stat.st_mtime_ns, stat.st_size

    def _configured_room_count(self) -> int:
        if self.config_path is None:
            return len(self._current_config().rooms)
        try:
            payload = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError):
            return len(self._current_config().rooms)
        rooms = payload.get("rooms", []) if isinstance(payload, dict) else []
        return len(rooms) if isinstance(rooms, list) else len(self._current_config().rooms)

    def reload_config(self) -> bool:
        if self.config_path is None:
            return False
        try:
            candidate = load_config(
                self.config_path,
                require_enabled_rooms=False,
            )
        except ConfigError as exc:
            message = _redact_error(str(exc))
            LOGGER.error("configuration_reload_rejected error=%s", message)
            self.health.update(
                heartbeat_at=time.time(),
                config_reload_error=message,
                last_error_category="configuration_invalid",
            )
            return False
        current = self._current_config()
        if candidate.storage.state_path != current.storage.state_path:
            message = "storage.state_path 运行时不可修改"
            LOGGER.error("configuration_reload_rejected error=%s", message)
            self.health.update(
                heartbeat_at=time.time(),
                config_reload_error=message,
                last_error_category="configuration_invalid",
            )
            return False
        enabled_urls = {room.url for room in candidate.rooms}
        with self._lock:
            self.config = candidate
            stop_keys = [
                key
                for key, room_url in self.recording_room_urls.items()
                if room_url not in enabled_urls
            ]
        now = time.time()
        self.health.update(
            heartbeat_at=now,
            configured_rooms=self._configured_room_count(),
            config_reloaded_at=now,
            config_reload_error="",
            poll_seconds=candidate.recorder.poll_seconds,
            storage_path=str(candidate.storage.path),
            min_free_gb=candidate.storage.min_free_gb,
        )
        LOGGER.info(
            "configuration_reloaded enabled_rooms=%d stopped_recordings=%d",
            len(candidate.rooms),
            len(stop_keys),
        )
        if stop_keys:
            threading.Thread(
                target=self.processes.stop,
                args=(stop_keys,),
                name="disabled-room-shutdown",
                daemon=True,
            ).start()
        self._wake_event.set()
        return True

    def _watch_config(self) -> None:
        while not self.shutdown_event.wait(1):
            fingerprint = self._fingerprint_config()
            if fingerprint == self._config_fingerprint:
                continue
            self._config_fingerprint = fingerprint
            self.reload_config()

    def _disk_available(self, config: AppConfig | None = None) -> bool:
        snapshot = config or self._current_config()
        free_gb = shutil.disk_usage(snapshot.storage.path).free / (1024**3)
        self.health.update(disk_free_gb=round(free_gb, 3))
        if free_gb < snapshot.storage.min_free_gb:
            LOGGER.error(
                "disk_space_low free_gb=%.2f required_gb=%.2f",
                free_gb,
                snapshot.storage.min_free_gb,
            )
            return False
        return True

    def _resolve(
        self, room: RoomConfig, config: AppConfig | None = None
    ) -> tuple[RoomConfig, dict[str, Any]]:
        snapshot = config or self._current_config()

        async def resolve() -> dict[str, Any]:
            resolver = (
                spider.get_douyin_app_stream_data
                if "v.douyin.com" in room.url or "/user/" in room.url
                else spider.get_douyin_web_stream_data
            )
            data = await resolver(
                room.url,
                proxy_addr=snapshot.proxy.url or None,
                cookies=snapshot.cookie or None,
            )
            result = await stream.get_douyin_stream_url(
                data,
                QUALITY_ALIASES[room.quality],
                snapshot.proxy.url or None,
            )
            result["room_id"] = data.get("id_str") or data.get("id") or data.get("room_id")
            result["web_rid"] = data.get("web_rid")
            identity = resolved_identity(data, result)
            if identity:
                result["_identity"] = identity
                self.identities.remember(room.url, identity)
            return result

        return room, asyncio.run(resolve())

    def _record(
        self,
        key: str,
        room: RoomConfig,
        result: dict[str, Any],
        config: AppConfig,
    ) -> None:
        stream_url = select_stream_url(result, config.recorder.stream_protocol)
        if not stream_url or self.shutdown_event.is_set() or not self._disk_available(config):
            return
        anchor = _safe_name(room.name or str(result.get("anchor_name") or key))
        output_dir = config.storage.path / anchor
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output = output_dir / f"{anchor}_{stamp}_%03d.ts"
        command = build_ffmpeg_command(
            stream_url,
            output,
            segment_seconds=config.recorder.segment_seconds,
            proxy_url=config.proxy.url,
        )
        try:
            managed = self.processes.start(key, command)
            LOGGER.info("recording_started room=%s anchor=%s", key, anchor)
            return_code = self.processes.wait(key)
            reason = classify_recording_end(
                return_code,
                "\n".join(managed.errors),
                stopping=self.shutdown_event.is_set(),
                disk_available=self._disk_available(config),
            )
            if reason == "ffmpeg_crash":
                self._ffmpeg_crashes += 1
            self.health.update(
                last_ffmpeg_return_code=return_code,
                last_ffmpeg_error=_redact_error(managed.errors[-1] if managed.errors else ""),
                last_error_category=reason,
                ffmpeg_crashes=self._ffmpeg_crashes,
            )
            LOGGER.info("recording_stopped room=%s code=%s reason=%s", key, return_code, reason)
            if (
                config.recorder.remux_to_mp4
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
                self.recording_room_urls.pop(key, None)

    @staticmethod
    def _room_key(room: RoomConfig, result: dict[str, Any]) -> str:
        identity = result.get("_identity")
        if identity:
            return str(identity)
        room_id = result.get("room_id") or result.get("web_rid")
        anchor = result.get("anchor_name")
        return str(room_id or anchor or room.url)

    def _handle_check_result(
        self, room: RoomConfig, result: dict[str, Any], config: AppConfig
    ) -> None:
        if self.shutdown_event.is_set():
            return
        if room.url not in {item.url for item in self._current_config().rooms}:
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
                args=(key, room, result, config),
                name=f"record-{_safe_name(key)}",
            )
            self.record_threads[key] = thread
            self.recording_room_urls[key] = room.url
            thread.start()

    def run(self) -> int:
        LOGGER.info(
            "daemon_started rooms=%d poll_seconds=%d cookie=%s",
            len(self._current_config().rooms),
            self._current_config().recorder.poll_seconds,
            redact_secret(self._current_config().cookie),
        )
        if not self._current_config().cookie:
            LOGGER.warning("douyin_cookie_missing some rooms or qualities may be unavailable")
        now = time.time()
        self.health.update(
            heartbeat_at=now,
            last_check_at=now,
            configured_rooms=self._configured_room_count(),
            poll_seconds=self._current_config().recorder.poll_seconds,
            storage_path=str(self._current_config().storage.path),
            min_free_gb=self._current_config().storage.min_free_gb,
            stopping=False,
        )
        watcher = None
        if self.config_path is not None:
            watcher = threading.Thread(
                target=self._watch_config,
                name="douyin-config-watcher",
                daemon=True,
            )
            watcher.start()
        failures = 0
        while not self.shutdown_event.is_set():
            config = self._current_config()
            if not self._disk_available(config):
                self.request_shutdown()
                break
            rooms = self.identities.deduplicate(config.rooms)
            futures = [self.pool.submit(self._resolve, room, config) for room in rooms]
            completed = 0
            for future in futures:
                if self.shutdown_event.is_set():
                    break
                try:
                    room, result = future.result(timeout=45)
                    self._handle_check_result(room, result, config)
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
                    self.health.update(last_error_category=category)
            now = time.time()
            self.health.update(
                heartbeat_at=now,
                last_check_at=now,
                check_failures=failures,
                check_failure_categories=self.observations.counters,
                ffmpeg_crashes=self._ffmpeg_crashes,
                active_recordings=len(self.processes.active_keys()),
                configured_rooms=self._configured_room_count(),
            )
            delay = config.recorder.poll_seconds if completed or not rooms else retry_delay(min(failures, 6))
            self._wake_event.wait(delay)
            self._wake_event.clear()
        self.pool.shutdown(wait=True, cancel_futures=True)
        self.processes.stop_all()
        for thread in list(self.record_threads.values()):
            thread.join(timeout=60)
        self.postprocess.shutdown(wait=True)
        if watcher is not None:
            watcher.join(timeout=2)
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
        config_path = Path(args.config)
        config = load_config(config_path, require_enabled_rooms=False)
    except ConfigError as exc:
        LOGGER.error("configuration_invalid error=%s", exc)
        return 2
    daemon = DouyinDaemon(config, config_path=config_path)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda signum, _frame, service=daemon: service.request_shutdown(signum))
    return daemon.run()


if __name__ == "__main__":
    sys.exit(main())
