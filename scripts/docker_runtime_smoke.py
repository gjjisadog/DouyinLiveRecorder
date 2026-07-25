"""Exercise both Docker targets, healthchecks, Web access and graceful FFmpeg stop."""

from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )


def docker_mount(source: Path, target: str, *, readonly: bool = False) -> str:
    options = f"type=bind,source={source.resolve()},target={target}"
    if readonly:
        options += ",readonly"
    return options


def wait_until(label: str, predicate, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except Exception as exc:  # noqa: BLE001 - surfaced after bounded retries
            last_error = exc
        time.sleep(0.5)
    detail = f": {last_error}" if last_error else ""
    raise RuntimeError(f"timed out waiting for {label}{detail}")


def inspect_json(image: str, template: str) -> object:
    output = run(["docker", "image", "inspect", "--format", template, image]).stdout.strip()
    return json.loads(output or "null")


def write_config(root: Path) -> None:
    config = root / "config"
    config.mkdir(parents=True)
    config_file = config / "douyin.yaml"
    config_file.write_text(
        """rooms:
  - url: https://live.douyin.com/123456
    name: smoke
    quality: sd
    enabled: true
recorder:
  format: ts
  segment_seconds: 60
  poll_seconds: 10
  max_concurrent_checks: 1
  stream_protocol: auto
  remux_to_mp4: false
  remux_workers: 1
  delete_source_after_remux: false
storage:
  path: /data/downloads
  state_path: /data/state
  min_free_gb: 0.1
proxy:
  url: ""
cookie:
  value: ""
notifications:
  enabled: false
""",
        encoding="utf-8",
    )
    if os.name != "nt":
        config.chmod(0o777)
        config_file.chmod(0o666)
    for name in ("downloads", "state", "logs", "backup_config"):
        path = root / name
        path.mkdir()
        if os.name != "nt":
            path.chmod(0o777)
    secrets = root / "secrets"
    secrets.mkdir()
    (secrets / "web_token").write_text("docker-smoke-web-token-1234567890\n", encoding="utf-8")
    if os.name != "nt":
        secrets.chmod(0o777)
        (secrets / "web_token").chmod(0o644)


def remove_container(name: str) -> None:
    run(["docker", "rm", "-f", name], check=False)


def container_diagnostics(name: str, root: Path) -> str:
    reports: list[str] = []
    for label, command in (
        ("container logs", ["docker", "logs", "--tail", "200", name]),
        ("container processes", ["docker", "top", name, "-eo", "pid,comm,args"]),
        (
            "container config metadata",
            [
                "docker",
                "exec",
                name,
                "python",
                "-c",
                (
                    "import hashlib,pathlib,yaml;"
                    "p=pathlib.Path('/app/config/douyin.yaml');"
                    "b=p.read_bytes();d=yaml.safe_load(b) or {};"
                    "print({'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),"
                    "'rooms':len(d.get('rooms',[]))})"
                ),
            ],
        ),
        (
            "container health",
            ["docker", "exec", name, "cat", "/data/state/health.json"],
        ),
    ):
        result = run(command, check=False)
        reports.append(f"{label}:\n{result.stdout}{result.stderr}".rstrip())
    for label, path in (
        ("host health", root / "state" / "health.json"),
    ):
        try:
            reports.append(f"{label}:\n{path.read_text(encoding='utf-8')}")
        except OSError as exc:
            reports.append(f"{label}: unreadable ({exc})")
    host_config = root / "config" / "douyin.yaml"
    try:
        content = host_config.read_bytes()
        reports.append(
            "host config metadata:\n"
            f"bytes={len(content)} sha256={hashlib.sha256(content).hexdigest()}"
        )
    except OSError as exc:
        reports.append(f"host config metadata: unreadable ({exc})")
    return "\n\n".join(reports)


def smoke_daemon(image: str, root: Path, name: str) -> None:
    run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--mount",
            docker_mount(root / "config", "/app/config", readonly=True),
            "--mount",
            docker_mount(root / "downloads", "/data/downloads"),
            "--mount",
            docker_mount(root / "state", "/data/state"),
            image,
        ]
    )
    wait_until(
        "daemon healthcheck",
        lambda: run(
            ["docker", "exec", name, "python", "-m", "app.health", "check"],
            check=False,
        ).returncode
        == 0,
    )
    ports = json.loads(
        run(["docker", "inspect", "--format", "{{json .NetworkSettings.Ports}}", name]).stdout
    )
    if ports:
        raise RuntimeError(f"daemon unexpectedly exposes ports: {ports}")
    run(["docker", "stop", "--time", "90", name])
    log_result = run(["docker", "logs", name])
    logs = log_result.stdout + log_result.stderr
    if "daemon_stopped" not in logs:
        raise RuntimeError("daemon did not report a graceful stop")


def smoke_nas_web(image: str, root: Path, name: str) -> None:
    token = (root / "secrets" / "web_token").read_text(encoding="utf-8").strip()
    run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "-p",
            "127.0.0.1::18091",
            "--mount",
            docker_mount(root / "config", "/app/config"),
            "--mount",
            docker_mount(root / "downloads", "/data/downloads"),
            "--mount",
            docker_mount(root / "state", "/data/state"),
            "--mount",
            docker_mount(root / "logs", "/app/logs"),
            "--mount",
            docker_mount(root / "backup_config", "/app/backup_config"),
            "--mount",
            docker_mount(root / "secrets" / "web_token", "/run/secrets/web_token", readonly=True),
            image,
        ]
    )

    base_url = ""

    def web_is_ready() -> bool:
        nonlocal base_url
        binding = run(["docker", "port", name, "18091/tcp"]).stdout.strip().splitlines()[0]
        port = binding.rsplit(":", 1)[1]
        base_url = f"http://127.0.0.1:{port}"
        request = urllib.request.Request(
            f"{base_url}/",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status == 200 and "daemon NAS" in response.read().decode("utf-8")

    wait_until("NAS Web endpoint", web_is_ready)
    unauthenticated = run(
        [
            "docker",
            "exec",
            name,
            "python",
            "-c",
            (
                "import urllib.request,urllib.error;"
                "\ntry: urllib.request.urlopen('http://127.0.0.1:18091/',timeout=3)"
                "\nexcept urllib.error.HTTPError as exc: raise SystemExit(0 if exc.code == 401 else 2)"
                "\nraise SystemExit(3)"
            ),
        ],
        check=False,
    )
    if unauthenticated.returncode != 0:
        raise RuntimeError("NAS management page did not require authentication")

    before_state = json.loads((root / "state" / "health.json").read_text(encoding="utf-8"))
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    page_request = urllib.request.Request(
        f"{base_url}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    with opener.open(page_request, timeout=5) as response:
        page = response.read().decode("utf-8")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page)
    if not csrf:
        raise RuntimeError("NAS Web page did not issue a CSRF token")
    payload = urllib.parse.urlencode(
        {
            "csrf_token": csrf.group(1),
            "url": "https://live.douyin.com/654321",
            "name": "hot-reload-smoke",
            "quality": "sd",
            "enabled": "1",
        }
    ).encode("utf-8")
    add_request = urllib.request.Request(
        f"{base_url}/rooms/add",
        data=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    with opener.open(add_request, timeout=5) as response:
        response.read()
    persisted_config = run(
        [
            "docker",
            "exec",
            name,
            "python",
            "-c",
            (
                "import pathlib,yaml;"
                "d=yaml.safe_load(pathlib.Path('/app/config/douyin.yaml').read_bytes()) or {};"
                "raise SystemExit(0 if len(d.get('rooms',[])) == 2 else 1)"
            ),
        ],
        check=False,
    )
    if persisted_config.returncode != 0:
        raise RuntimeError(
            "NAS Web did not persist the added room\n\n"
            f"{container_diagnostics(name, root)}"
        )
    try:
        wait_until(
            "daemon YAML hot reload",
            lambda: (
                (
                    current_state := json.loads(
                        (root / "state" / "health.json").read_text(encoding="utf-8")
                    )
                ).get("configured_rooms")
                == 2
                and bool(current_state.get("config_reloaded_at"))
            ),
        )
    except RuntimeError as exc:
        raise RuntimeError(f"{exc}\n\n{container_diagnostics(name, root)}") from exc
    after_state = json.loads((root / "state" / "health.json").read_text(encoding="utf-8"))
    if after_state.get("started_at") != before_state.get("started_at"):
        raise RuntimeError("daemon restarted instead of hot-loading YAML")
    if not after_state.get("config_reloaded_at"):
        raise RuntimeError("daemon did not report a successful YAML hot reload")
    process_list = run(["docker", "top", name, "-eo", "pid,comm,args"]).stdout.lower()
    if "main.py" in process_list or "app.douyin_daemon" not in process_list:
        raise RuntimeError(f"NAS launcher used an unexpected recorder entrypoint: {process_list}")
    wait_until(
        "NAS healthcheck",
        lambda: run(
            ["docker", "exec", name, "python", "-m", "client.infra.docker.healthcheck"],
            check=False,
        ).returncode
        == 0,
    )
    run(["docker", "stop", "--time", "90", name])
    log_result = run(["docker", "logs", name])
    logs = log_result.stdout + log_result.stderr
    if "recorder stop stage=SIGINT" not in logs or "daemon_stopped" not in logs:
        raise RuntimeError("NAS launcher did not gracefully stop its daemon child")
    stopped_processes = run(["docker", "top", name, "-eo", "pid,comm,args"], check=False)
    if stopped_processes.returncode == 0 and "ffmpeg" in stopped_processes.stdout.lower():
        raise RuntimeError("FFmpeg remained after stopping the NAS container")


def smoke_ffmpeg_stop(image: str, root: Path, name: str) -> None:
    run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--mount",
            docker_mount(root / "downloads", "/data/downloads"),
            "--entrypoint",
            "python",
            image,
            "-m",
            "scripts.docker_ffmpeg_fixture",
        ]
    )
    wait_until("FFmpeg fixture", lambda: (root / "downloads" / "fixture.ready").exists())
    process_list = run(["docker", "top", name, "-eo", "pid,comm,args"]).stdout
    if "ffmpeg" not in process_list:
        raise RuntimeError("FFmpeg fixture process was not running before docker stop")
    run(["docker", "stop", "--time", "90", name])
    state = run(["docker", "inspect", "--format", "{{.State.Running}}", name]).stdout.strip()
    if state != "false":
        raise RuntimeError("fixture container is still running after docker stop")
    stopped_processes = run(["docker", "top", name, "-eo", "pid,comm,args"], check=False)
    if stopped_processes.returncode == 0 and "ffmpeg" in stopped_processes.stdout.lower():
        raise RuntimeError("FFmpeg process remained after docker stop")
    media_files = sorted((root / "downloads").glob("fixture_*.ts"))
    if not media_files:
        raise RuntimeError("FFmpeg fixture did not produce a TS file")
    run(
        [
            "docker",
            "run",
            "--rm",
            "--mount",
            docker_mount(root / "downloads", "/data/downloads", readonly=True),
            "--entrypoint",
            "ffprobe",
            image,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            f"/data/downloads/{media_files[-1].name}",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--daemon-image", required=True)
    parser.add_argument("--nas-image", required=True)
    args = parser.parse_args()

    daemon_cmd = inspect_json(args.daemon_image, "{{json .Config.Cmd}}")
    nas_cmd = inspect_json(args.nas_image, "{{json .Config.Cmd}}")
    daemon_health = inspect_json(args.daemon_image, "{{json .Config.Healthcheck.Test}}")
    nas_health = inspect_json(args.nas_image, "{{json .Config.Healthcheck.Test}}")
    if daemon_cmd != ["python", "-m", "app.douyin_daemon"]:
        raise RuntimeError(f"unexpected daemon CMD: {daemon_cmd}")
    if nas_cmd != ["python", "-m", "client.infra.docker.launcher"]:
        raise RuntimeError(f"unexpected NAS CMD: {nas_cmd}")
    if daemon_health != ["CMD", "python", "-m", "app.health", "check"]:
        raise RuntimeError(f"unexpected daemon healthcheck: {daemon_health}")
    if nas_health != ["CMD", "python", "-m", "client.infra.docker.healthcheck"]:
        raise RuntimeError(f"unexpected NAS healthcheck: {nas_health}")

    suffix = uuid.uuid4().hex[:8]
    names = {
        "daemon": f"dlr-daemon-smoke-{suffix}",
        "nas": f"dlr-nas-smoke-{suffix}",
        "ffmpeg": f"dlr-ffmpeg-smoke-{suffix}",
    }
    with tempfile.TemporaryDirectory(prefix="dlr-docker-smoke-") as temporary:
        root = Path(temporary)
        write_config(root)
        try:
            smoke_daemon(args.daemon_image, root, names["daemon"])
            smoke_nas_web(args.nas_image, root, names["nas"])
            smoke_ffmpeg_stop(args.nas_image, root, names["ffmpeg"])
        finally:
            for name in names.values():
                remove_container(name)
    print(
        "Docker runtime smoke passed: authenticated YAML hot reload, shared HealthState, "
        "SIGINT stop, no residual FFmpeg and ffprobe."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
