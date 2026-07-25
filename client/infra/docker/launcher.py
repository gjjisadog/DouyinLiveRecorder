from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from client.infra.docker.config_web import create_server
from client.infra.docker.healthcheck import read_url_entries

DEFAULT_APP_ROOT = Path("/app")
DEFAULT_RESTART_DELAY_SECONDS = 5


class DockerLauncher:
    def __init__(self, app_root: Path) -> None:
        self.app_root = app_root
        self.server = None
        self.server_thread = None
        self.child: subprocess.Popen[str] | None = None
        self._stop_once = threading.Lock()
        self._stop_event = threading.Event()
        self._waiting_for_config_logged = False
        self.restart_delay_seconds = int(os.environ.get("DLR_RECORDER_RESTART_DELAY", str(DEFAULT_RESTART_DELAY_SECONDS)))
        self.config_path = Path(os.environ.get("DLR_WEB_CONFIG_PATH", str(self.app_root / "config" / "URL_config.ini")))

    def start(self) -> None:
        host = os.environ.get("DLR_WEB_HOST", "0.0.0.0").strip() or "0.0.0.0"
        port = int(os.environ.get("DLR_WEB_PORT", "18091"))
        self.server = create_server(config_path=self.config_path, host=host, port=port)
        self.server_thread = threading.Thread(target=self.server.serve_forever, name="docker-config-web", daemon=True)
        self.server_thread.start()
        print(f"[docker-config-web] serving http://{host}:{port} for {self.config_path}")

    def _start_recorder(self) -> None:
        command = [sys.executable, "main.py"]
        print("[docker-launcher] starting recorder process")
        self.child = subprocess.Popen(command, cwd=self.app_root, text=True)
        self._waiting_for_config_logged = False

    def wait(self) -> int:
        while not self._stop_event.is_set():
            entries = read_url_entries(self.config_path)
            if self.child is not None:
                return_code = self.child.poll()
                if return_code is None:
                    time.sleep(1)
                    continue
                print(f"[docker-launcher] recorder exited with code {return_code}")
                self.child = None
                if entries:
                    print(f"[docker-launcher] retrying recorder in {self.restart_delay_seconds} seconds")
                    self._stop_event.wait(self.restart_delay_seconds)
                    continue
            if entries:
                self._start_recorder()
                continue
            if not self._waiting_for_config_logged:
                print(f"[docker-launcher] waiting for live room configuration in {self.config_path}")
                self._waiting_for_config_logged = True
            self._stop_event.wait(1)
        return 0

    def stop(self) -> None:
        with self._stop_once:
            self._stop_event.set()
            if self.server is not None:
                self.server.shutdown()
                self.server.server_close()
                self.server = None
            if self.child is not None and self.child.poll() is None:
                self.child.terminate()
                try:
                    self.child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    self.child.kill()
                    self.child.wait(timeout=10)
            self.child = None


def main() -> int:
    app_root = Path(os.environ.get("DLR_APP_ROOT", str(DEFAULT_APP_ROOT)))
    launcher = DockerLauncher(app_root=app_root)

    def handle_signal(signum: int, _frame: object) -> None:
        print(f"[docker-launcher] received signal {signum}, shutting down")
        launcher.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_signal)

    launcher.start()
    try:
        return launcher.wait()
    finally:
        launcher.stop()


if __name__ == "__main__":
    raise SystemExit(main())
