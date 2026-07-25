from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from client.infra.docker.config_web import create_server

DEFAULT_APP_ROOT = Path("/app")
DEFAULT_RESTART_DELAY_SECONDS = 5
DEFAULT_INTERRUPT_TIMEOUT_SECONDS = 30
DEFAULT_TERMINATE_TIMEOUT_SECONDS = 30
DEFAULT_KILL_TIMEOUT_SECONDS = 10
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
        self.daemon_config_path = Path(
            os.environ.get("DOUYIN_CONFIG", str(self.app_root / "config" / "douyin.yaml"))
        )
        self.log_dir = Path(os.environ.get("DLR_WEB_LOG_DIR", str(self.app_root / "logs")))
        self.state_path = Path(os.environ.get("DLR_STATE_PATH", "/data/state"))
        self.token_file = Path(
            os.environ.get("DLR_WEB_TOKEN_FILE", "/run/secrets/web_token")
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
        self.server = create_server(
            config_path=self.daemon_config_path,
            log_dir=self.log_dir,
            state_path=self.state_path,
            host=host,
            port=port,
            token_file=self.token_file,
        )
        self.server_thread = threading.Thread(
            target=self.server.serve_forever,
            name="docker-config-web",
        )
        self.server_thread.start()
        print(f"[docker-config-web] serving host={host} port={port} config={self.daemon_config_path}")

    def _recorder_command(self) -> list[str]:
        return [sys.executable, "-m", "app.douyin_daemon"]

    def _recorder_is_configured(self) -> bool:
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
        print("[docker-launcher] starting recorder module=app.douyin_daemon")
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
                print(
                    f"[docker-launcher] waiting for recorder configuration in {self.daemon_config_path}"
                )
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
                self.server.stop_accepting_writes()
                self.server.shutdown()
            self._stop_child()
            if self.server is not None:
                self.server.server_close()
                self.server = None
            if self.server_thread is not None:
                self.server_thread.join(timeout=30)
                self.server_thread = None


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
