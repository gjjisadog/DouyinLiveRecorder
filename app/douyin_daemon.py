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
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

from src import spider, stream, utils
from src.http_clients.async_http import use_async_client

from .config import ConfigError, QUALITY_ALIASES, load_config, redact_secret
from .health import HealthState
from .identity_cache import IdentityCache, resolved_identity
from .models import AppConfig, RoomConfig
from .observations import ObservationStore, classify_check_failure
from .postprocess import PostProcessQueue
from .process_manager import ProcessManager, build_ffmpeg_command
from .runtime_state import FfmpegCrashTracker, RoomRuntimeState

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
        self._event_loop: asyncio.AbstractEventLoop | None = None
        self._async_wake: asyncio.Event | None = None
        self.processes = ProcessManager()
        self.health = HealthState(config.storage.state_path)
        self.identities = IdentityCache(config.storage.state_path)
        self.observations = ObservationStore(config.storage.state_path)
        self.record_threads: dict[str, threading.Thread] = {}
        self.recording_room_urls: dict[str, str] = {}
        self.room_states: dict[str, RoomRuntimeState] = {}
        self._check_tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = threading.RLock()
        self._config_fingerprint = self._fingerprint_config()
        self.ffmpeg_health = FfmpegCrashTracker()
        self.http_client: httpx.AsyncClient | None = None
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
            self._notify_scheduler()
            self.health.update(stopping=True, heartbeat_at=time.time())

    def _notify_scheduler(self) -> None:
        loop = self._event_loop
        wake = self._async_wake
        if loop is not None and wake is not None and loop.is_running():
            loop.call_soon_threadsafe(wake.set)

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
        self._notify_scheduler()
        return True

    async def _watch_config(self) -> None:
        while not self.shutdown_event.is_set():
            await asyncio.sleep(1)
            fingerprint = self._fingerprint_config()
            if fingerprint == self._config_fingerprint:
                continue
            self._config_fingerprint = fingerprint
            await asyncio.to_thread(self.reload_config)

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

    async def _resolve(
        self, room: RoomConfig, config: AppConfig | None = None
    ) -> tuple[RoomConfig, dict[str, Any]]:
        snapshot = config or self._current_config()
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
        return room, result

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
            protocol="hls" if ".m3u8" in stream_url.lower() else "flv",
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
            with self._lock:
                if reason == "ffmpeg_crash":
                    self.ffmpeg_health.record_crash()
                elif reason == "stream_ended":
                    self.ffmpeg_health.record_success()
                crash_state = self.ffmpeg_health.snapshot()
            self.health.update(
                last_ffmpeg_return_code=return_code,
                last_ffmpeg_error=_redact_error(managed.errors[-1] if managed.errors else ""),
                last_error_category=reason,
                **crash_state,
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
            with self._lock:
                self.ffmpeg_health.record_crash()
                crash_state = self.ffmpeg_health.snapshot()
            self.health.update(last_error_category="ffmpeg_crash", **crash_state)
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

    def _sync_room_states(self, rooms: tuple[RoomConfig, ...]) -> None:
        urls = {room.url for room in rooms}
        for url in urls:
            self.room_states.setdefault(url, RoomRuntimeState(url=url))
        for url in set(self.room_states) - urls:
            self.room_states.pop(url, None)
            task = self._check_tasks.pop(url, None)
            if task is not None:
                task.cancel()

    def _scheduler_metrics(self) -> dict[str, Any]:
        states = tuple(self.room_states.values())
        checks = sum(state.checks for state in states)
        successes = sum(state.successes for state in states)
        return {
            "room_checks_total": checks,
            "room_check_successes": successes,
            "room_check_failures": checks - successes,
            "check_failures": checks - successes,
            "room_check_success_rate": round(successes / checks, 6) if checks else 0.0,
            "rooms_in_backoff": sum(state.consecutive_failures > 0 for state in states),
            "last_check_at": max((state.last_check_at for state in states), default=time.time()),
        }

    async def _check_room(
        self,
        room: RoomConfig,
        config: AppConfig,
        semaphore: asyncio.Semaphore,
    ) -> None:
        state = self.room_states.setdefault(room.url, RoomRuntimeState(url=room.url))
        try:
            async with semaphore:
                resolved_room, result = await asyncio.wait_for(
                    self._resolve(room, config),
                    timeout=45,
                )
            if room.url not in {item.url for item in self._current_config().rooms}:
                return
            self._handle_check_result(resolved_room, result, config)
            state.record_success(now=time.time(), poll_seconds=config.recorder.poll_seconds)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            category = classify_check_failure(str(exc))
            fingerprint = self.observations.record(category, exc)
            delay = retry_delay(state.consecutive_failures)
            state.record_failure(now=time.time(), category=category, delay=delay)
            LOGGER.error(
                "room_check_failed category=%s error_type=%s fingerprint=%s retry_seconds=%.2f",
                category,
                type(exc).__name__,
                fingerprint,
                delay,
            )
            await self.health.update_async(last_error_category=category)
        finally:
            await self.health.update_async(
                heartbeat_at=time.time(),
                check_failure_categories=self.observations.counters,
                active_recordings=len(self.processes.active_keys()),
                configured_rooms=self._configured_room_count(),
                **self._scheduler_metrics(),
            )

    async def _scheduler(self) -> None:
        semaphore = asyncio.Semaphore(self._current_config().recorder.max_concurrent_checks)
        while not self.shutdown_event.is_set():
            config = self._current_config()
            if not await asyncio.to_thread(self._disk_available, config):
                self.request_shutdown()
                break
            rooms = self.identities.deduplicate(config.rooms)
            self._sync_room_states(rooms)
            now = time.time()
            for room in rooms:
                state = self.room_states[room.url]
                current = self._check_tasks.get(room.url)
                if current is not None and not current.done():
                    continue
                if current is not None:
                    self._check_tasks.pop(room.url, None)
                if state.next_check_at <= now:
                    self._check_tasks[room.url] = asyncio.create_task(
                        self._check_room(room, config, semaphore),
                        name=f"check-{_safe_name(room.url)}",
                    )
            await self.health.update_async(
                heartbeat_at=time.time(),
                active_recordings=len(self.processes.active_keys()),
                configured_rooms=self._configured_room_count(),
                **self._scheduler_metrics(),
            )
            wake = self._async_wake
            if wake is None:
                await asyncio.sleep(0.5)
                continue
            try:
                await asyncio.wait_for(wake.wait(), timeout=0.5)
            except asyncio.TimeoutError:
                pass
            wake.clear()

    def _make_http_client(self) -> httpx.AsyncClient:
        config = self._current_config()
        return httpx.AsyncClient(
            proxy=utils.handle_proxy_addr(config.proxy.url or None),
            timeout=httpx.Timeout(30.0, connect=15.0),
            limits=httpx.Limits(
                max_connections=max(8, config.recorder.max_concurrent_checks * 4),
                max_keepalive_connections=max(4, config.recorder.max_concurrent_checks * 2),
                keepalive_expiry=30.0,
            ),
            follow_redirects=True,
            http2=True,
        )

    async def run_async(self) -> int:
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
        self._event_loop = asyncio.get_running_loop()
        self._async_wake = asyncio.Event()
        self.http_client = self._make_http_client()
        watcher: asyncio.Task[None] | None = None
        if self.config_path is not None:
            watcher = asyncio.create_task(
                self._watch_config(),
                name="douyin-config-watcher",
            )
        try:
            with use_async_client(self.http_client):
                await self._scheduler()
        finally:
            if watcher is not None:
                watcher.cancel()
            for task in self._check_tasks.values():
                task.cancel()
            pending = list(self._check_tasks.values())
            if watcher is not None:
                pending.append(watcher)
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            await asyncio.to_thread(self.processes.stop_all)
            for thread in list(self.record_threads.values()):
                await asyncio.to_thread(thread.join, 60)
            await asyncio.to_thread(self.postprocess.shutdown, True)
            await self.http_client.aclose()
            self.http_client = None
            await self.health.update_async(
                heartbeat_at=time.time(),
                active_recordings=0,
                stopping=True,
                **self.ffmpeg_health.snapshot(),
            )
            LOGGER.info("daemon_stopped")
        return 0

    def run(self) -> int:
        return asyncio.run(self.run_async())


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
