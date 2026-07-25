from __future__ import annotations

import logging
import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from .process_manager import ProcessManager, build_remux_command

LOGGER = logging.getLogger("douyin-daemon.postprocess")


class PostProcessQueue:
    def __init__(
        self,
        process_manager: ProcessManager,
        *,
        workers: int,
        delete_source: bool,
        stopping: threading.Event,
    ) -> None:
        self.process_manager = process_manager
        self.delete_source = delete_source
        self.stopping = stopping
        self._executor = ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="remux",
        )
        self._lock = threading.Lock()
        self._futures: set[Future[bool]] = set()

    def submit(self, source: Path) -> bool:
        if self.stopping.is_set() or source.suffix.lower() != ".ts" or not source.is_file():
            return False
        future = self._executor.submit(self._remux, source)
        with self._lock:
            self._futures.add(future)
        future.add_done_callback(self._discard)
        return True

    def _discard(self, future: Future[bool]) -> None:
        with self._lock:
            self._futures.discard(future)
        try:
            future.result()
        except Exception:
            LOGGER.exception("remux_worker_failed")

    def _remux(self, source: Path) -> bool:
        if self.stopping.is_set():
            return False
        destination = source.with_suffix(".mp4")
        temporary = destination.with_suffix(".mp4.partial")
        key = f"remux:{source.resolve()}"
        managed = self.process_manager.start(key, build_remux_command(source, temporary))
        return_code = self.process_manager.wait(key)
        if return_code != 0 or not temporary.is_file():
            temporary.unlink(missing_ok=True)
            LOGGER.error("remux_failed source=%s code=%d", source.name, return_code)
            return False
        os.replace(temporary, destination)
        if self.delete_source:
            source.unlink(missing_ok=True)
        LOGGER.info("remux_completed source=%s output=%s", source.name, destination.name)
        return True

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=True)
