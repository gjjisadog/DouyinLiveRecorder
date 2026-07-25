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
DEFAULT_INTERRUPT_TIMEOUT_SECONDS = 30
DEFAULT_TERMINATE_TIMEOUT_SECONDS = 30
DEFAULT_KILL_TIMEOUT_SECONDS = 10
RECORDER_MODES = {"daemon", "legacy"}
KILL_SIGNAL = getattr(signal, "SIGKILL", getattr(signal, "SIGBREAK", signal.SIGTERM))


class DockerLauncher:
    def __init__(self, app_root: Path) -> None:
        self.app_root = app_root
        self.server = None
        self.server_thread = None
        self.child: subprocess.Popen[str] | None = None
        self._stop_once = threading.RLock()
        self._stop_event = threading.Event()
        self._stopped = False
        self._waiting_for_config_logged = False
        self.restart_delay_seconds = int(os.environ.get("DLR_RECORDER_RESTART_DELAY", str(DEFAULT_RESTART_DELAY_SECONDS)))
        self.config_path = Path(os.environ.get("DLR_WEB_CONFIG_PATH", str(self.app_root / "config" / "URL_config.ini")))
        self.recorder_mode = os.environ.get("DLR_RECORDER_MODE", "daemon").strip().lower()
        if self.recorder_mode not in RECORDER_MODES:
            raise ValueError(f"Unsupported DLR_RECORDER_MODE: {self.recorder_mode}")
        self.daemon_config_path = Path(
            os.environ.get("DOUYIN_CONFIG", str(self.app_root / "config" / "douyin.yaml"))
        )
        self.interrupt_timeout = float(
            os.environ.get("DLR_STOP_INTERRUPT_TIMEOUT", str(DEFAULT_INTERRUPT_TIMEOUT_SECONDS))
        )
        self.terminate_timeout = float(
            os.environ.get("DLR_STOP_TERMINATE_TIMEOUT", str(DEFAULT_TERMINATE_TIMEOUT_SECONDS))
        )
        self.kill_timeout = float(
            os.environ.get("DLR_STOP_KILL_TIMEOUT", str(DEFAULT_KILL_TIMEOUT_SECONDS))
        )

    def start(self) -> None:
        host = os.environ.get("DLR_WEB_HOST", "0.0.0.0").strip() or "0.0.0.0"
        port = int(os.environ.get("DLR_WEB_PORT", "18091"))
        self.server = create_server(config_path=self.config_path, host=host, port=port)
        self.server_thread = threading.Thread(target=self.server.serve_forever, name="docker-config-web", daemon=True)
        self.server_thread.start()
        print(f"[docker-config-web] serving http://{host}:{port} for {self.config_path}")

    def _recorder_command(self) -> list[str]:
        if self.recorder_mode == "legacy":
            return [sys.executable, "main.py"]
        return [sys.executable, "-m", "app.douyin_daemon"]

    def _recorder_is_configured(self) -> bool:
        if self.recorder_mode == "legacy":
            return bool(read_url_entries(self.config_path))
        return self.daemon_config_path.is_file()

    def _start_recorder(self) -> None:
        command = self._recorder_command()
        popen_kwargs: dict[str, object] = {
            "cwd": self.app_root,
            "text": True,
        }
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True
        print(f"[docker-launcher] starting recorder mode={self.recorder_mode}")
        self.child = subprocess.Popen(command, **popen_kwargs)
        self._waiting_for_config_logged = False

    def wait(self) -> int:
        while not self._stop_event.is_set():
            configured = self._recorder_is_configured()
            if self.child is not None:
                return_code = self.child.poll()
                if return_code is None:
                    time.sleep(1)
                    continue
                print(f"[docker-launcher] recorder exited with code {return_code}")
                self.child = None
                if configured:
                    print(f"[docker-launcher] retrying recorder in {self.restart_delay_seconds} seconds")
                    self._stop_event.wait(self.restart_delay_seconds)
                    continue
            if configured:
                self._start_recorder()
                continue
            if not self._waiting_for_config_logged:
                expected_path = self.config_path if self.recorder_mode == "legacy" else self.daemon_config_path
                print(f"[docker-launcher] waiting for recorder configuration in {expected_path}")
                self._waiting_for_config_logged = True
            self._stop_event.wait(1)
        return 0

    @staticmethod
    def _send_signal_to_child_group(child: subprocess.Popen[str], sig: int) -> None:
        if child.poll() is not None:
            return
        if os.name == "nt":
            if sig == signal.SIGINT:
                child.send_signal(signal.CTRL_BREAK_EVENT)
            elif sig == signal.SIGTERM:
                child.terminate()
            else:
                child.kill()
            return
        os.killpg(os.getpgid(child.pid), sig)

    @staticmethod
    def _wait_for_child(child: subprocess.Popen[str], timeout: float) -> bool:
        try:
            child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return False
        return True

    def _stop_child(self) -> None:
        child = self.child
        if child is None or child.poll() is not None:
            self.child = None
            return
        stages = (
            (signal.SIGINT, self.interrupt_timeout, "SIGINT"),
            (signal.SIGTERM, self.terminate_timeout, "terminate"),
            (KILL_SIGNAL, self.kill_timeout, "kill"),
        )
        for sig, timeout, label in stages:
            if child.poll() is not None:
                break
            print(f"[docker-launcher] recorder stop stage={label}")
            try:
                self._send_signal_to_child_group(child, sig)
            except ProcessLookupError:
                break
            if self._wait_for_child(child, timeout):
                break
        self.child = None

    def stop(self) -> None:
        with self._stop_once:
            if self._stopped:
                return
            self._stopped = True
            self._stop_event.set()
            if self.server is not None:
                self.server.shutdown()
                self.server.server_close()
                self.server = None
            self._stop_child()


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
