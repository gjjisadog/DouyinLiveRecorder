"""SSH deployment helpers for FlyInNAS/NAS hosts."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import subprocess
import tarfile
import tempfile

from client.version import APP_VERSION

DEFAULT_REMOTE_DIR = "/vol1/docker/douyin-live-recorder"
DEFAULT_REMOTE_PYTHON = "python3"
DEFAULT_DEPLOY_SCENARIOS = ("first-deploy", "upgrade-deploy", "rollback-deploy")
DEFAULT_EXCLUDES = {
    ".git",
    ".client-conda-env",
    "build",
    "dist",
    "client_data",
    "logs",
    "downloads",
    "backup_config",
    "__pycache__",
    ".pytest_cache",
}


@dataclass(slots=True)
class DeployTarget:
    host: str
    user: str
    port: int = 22
    identity_file: Path | None = None

    @property
    def destination(self) -> str:
        return f"{self.user}@{self.host}"


def normalize_remote_dir(remote_dir: str) -> str:
    normalized = remote_dir.strip().rstrip("/")
    return normalized or DEFAULT_REMOTE_DIR


def bundle_basename(version: str = APP_VERSION) -> str:
    return f"douyin-live-recorder-flyinnas-{version}.tar.gz"


def should_exclude(relative_path: Path) -> bool:
    parts = relative_path.parts
    if not parts:
        return False
    if parts[0] in DEFAULT_EXCLUDES:
        return True
    if any(part.startswith("tmp") for part in parts):
        return True
    if any(part.endswith(".pyc") for part in parts):
        return True
    return False


def create_deploy_bundle(repo_root: Path, bundle_path: Path) -> Path:
    root = repo_root.resolve()
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(bundle_path, "w:gz") as archive:
        for file_path in sorted(path for path in root.rglob("*") if path.is_file()):
            relative_path = file_path.relative_to(root)
            if should_exclude(relative_path):
                continue
            if relative_path.parts[0] == "config":
                continue
            archive.add(file_path, arcname=Path("app") / relative_path)
        for config_name in ("config.ini", "URL_config.ini", "douyin.yaml"):
            config_path = root / "config" / config_name
            if config_path.exists():
                archive.add(config_path, arcname=Path("config_templates") / config_name)
    return bundle_path


def build_scp_command(bundle_path: Path, target: DeployTarget, remote_bundle_path: str) -> list[str]:
    command = ["scp", "-P", str(target.port)]
    if target.identity_file is not None:
        command.extend(["-i", str(target.identity_file)])
    command.extend([str(bundle_path), f"{target.destination}:{remote_bundle_path}"])
    return command


def build_ssh_command(target: DeployTarget, extra_args: list[str] | None = None) -> list[str]:
    command = ["ssh", "-p", str(target.port)]
    if target.identity_file is not None:
        command.extend(["-i", str(target.identity_file)])
    command.append(target.destination)
    if extra_args:
        command.extend(extra_args)
    return command


def render_remote_script() -> str:
    return """#!/bin/sh
set -eu

APP_ROOT="$1"
ARCHIVE_PATH="$2"
SCENARIO="$3"
REMOTE_PYTHON="$4"
EXPECTED_TAG="${5:-}"
IMAGE_REPOSITORY="${6:-}"

TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
  rm -f "$ARCHIVE_PATH"
}

upsert_env_key() {
  FILE_PATH="$1"
  ENV_KEY="$2"
  ENV_VALUE="$3"
  mkdir -p "$(dirname "$FILE_PATH")"
  touch "$FILE_PATH"
  TMP_ENV="${FILE_PATH}.tmp"
  awk -v key="$ENV_KEY" -v value="$ENV_VALUE" '
    BEGIN { updated = 0 }
    index($0, key "=") == 1 { print key "=" value; updated = 1; next }
    { print }
    END { if (!updated) print key "=" value }
  ' "$FILE_PATH" > "$TMP_ENV"
  mv "$TMP_ENV" "$FILE_PATH"
}

trap cleanup EXIT

mkdir -p "$APP_ROOT" "$APP_ROOT/config" "$APP_ROOT/logs" "$APP_ROOT/backup_config" "$APP_ROOT/downloads" "$APP_ROOT/client_data/docker-state"
tar -xzf "$ARCHIVE_PATH" -C "$TMP_DIR"

if [ -d "$TMP_DIR/app" ]; then
  cp -R "$TMP_DIR/app/." "$APP_ROOT/"
fi

if [ ! -f "$APP_ROOT/config/config.ini" ] && [ -f "$TMP_DIR/config_templates/config.ini" ]; then
  cp "$TMP_DIR/config_templates/config.ini" "$APP_ROOT/config/config.ini"
fi

if [ ! -f "$APP_ROOT/config/URL_config.ini" ] && [ -f "$TMP_DIR/config_templates/URL_config.ini" ]; then
  cp "$TMP_DIR/config_templates/URL_config.ini" "$APP_ROOT/config/URL_config.ini"
fi

if [ ! -f "$APP_ROOT/config/douyin.yaml" ] && [ -f "$TMP_DIR/config_templates/douyin.yaml" ]; then
  cp "$TMP_DIR/config_templates/douyin.yaml" "$APP_ROOT/config/douyin.yaml"
fi

if [ -n "$IMAGE_REPOSITORY" ] || [ -n "$EXPECTED_TAG" ]; then
  ENV_FILE="$APP_ROOT/.env"
  if [ -n "$IMAGE_REPOSITORY" ]; then
    upsert_env_key "$ENV_FILE" "DLR_IMAGE_REPOSITORY" "$IMAGE_REPOSITORY"
  fi
  if [ -n "$EXPECTED_TAG" ]; then
    upsert_env_key "$ENV_FILE" "DLR_IMAGE_TAG" "$EXPECTED_TAG"
  fi
fi

docker compose -f "$APP_ROOT/docker-compose.flyinnas.yaml" up -d --build

if [ -n "$EXPECTED_TAG" ]; then
  "$REMOTE_PYTHON" -m client.infra.docker.flyinnas_regression "$SCENARIO" --app-root "$APP_ROOT" --expected-tag "$EXPECTED_TAG"
else
  "$REMOTE_PYTHON" -m client.infra.docker.flyinnas_regression "$SCENARIO" --app-root "$APP_ROOT"
fi
"""


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    run_kwargs = {
        "cwd": str(cwd) if cwd is not None else None,
        "capture_output": False,
        "check": True,
    }
    if input_text is None:
        return subprocess.run(
            command,
            text=True,
            **run_kwargs,
        )
    # Keep LF line endings when piping the remote shell script over SSH from Windows.
    return subprocess.run(
        command,
        input=input_text.replace("\r\n", "\n").encode("utf-8"),
        text=False,
        **run_kwargs,
    )


def deploy_over_ssh(
    *,
    repo_root: Path,
    target: DeployTarget,
    remote_dir: str,
    scenario: str,
    remote_python: str = DEFAULT_REMOTE_PYTHON,
    expected_tag: str = APP_VERSION,
    image_repository: str = "",
    dry_run: bool = False,
) -> tuple[list[str], list[str]]:
    resolved_remote_dir = normalize_remote_dir(remote_dir)
    remote_bundle_path = f"/tmp/{bundle_basename(expected_tag or APP_VERSION)}"
    with tempfile.TemporaryDirectory(prefix="flyinnas_deploy_") as temp_dir:
        bundle_path = create_deploy_bundle(
            repo_root=repo_root,
            bundle_path=Path(temp_dir) / bundle_basename(expected_tag or APP_VERSION),
        )
        scp_command = build_scp_command(bundle_path, target, remote_bundle_path)
        ssh_args = [
            "sh",
            "-s",
            "--",
            resolved_remote_dir,
            remote_bundle_path,
            scenario,
            remote_python,
            expected_tag,
            image_repository,
        ]
        ssh_command = build_ssh_command(target, ssh_args)
        if dry_run:
            return scp_command, ssh_command
        run_command(scp_command, cwd=repo_root)
        run_command(ssh_command, cwd=repo_root, input_text=render_remote_script())
        return scp_command, ssh_command


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy the project to FlyInNAS over SSH.")
    parser.add_argument("--host", required=True, help="FlyInNAS host or IP.")
    parser.add_argument("--user", required=True, help="SSH username.")
    parser.add_argument("--port", type=int, default=22, help="SSH port.")
    parser.add_argument(
        "--remote-dir",
        default=DEFAULT_REMOTE_DIR,
        help="Remote project directory on FlyInNAS.",
    )
    parser.add_argument(
        "--scenario",
        choices=DEFAULT_DEPLOY_SCENARIOS,
        default="first-deploy",
        help="Deployment scenario used for remote regression.",
    )
    parser.add_argument(
        "--remote-python",
        default=DEFAULT_REMOTE_PYTHON,
        help="Remote Python executable used to run the FlyInNAS regression script.",
    )
    parser.add_argument(
        "--expected-tag",
        default=APP_VERSION,
        help="Expected Docker image tag after deployment. Override for rollback.",
    )
    parser.add_argument(
        "--image-repository",
        default="",
        help="Optional Docker image repository written into remote .env before compose up.",
    )
    parser.add_argument(
        "--identity-file",
        default="",
        help="Optional SSH private key path.",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Local repository root to upload.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved scp/ssh commands without executing them.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    target = DeployTarget(
        host=args.host,
        user=args.user,
        port=args.port,
        identity_file=Path(args.identity_file).resolve() if args.identity_file else None,
    )
    repo_root = Path(args.repo_root).resolve()
    scp_command, ssh_command = deploy_over_ssh(
        repo_root=repo_root,
        target=target,
        remote_dir=args.remote_dir,
        scenario=args.scenario,
        remote_python=args.remote_python,
        expected_tag=args.expected_tag,
        image_repository=args.image_repository,
        dry_run=args.dry_run,
    )
    print("SCP command:")
    print(" ".join(shlex.quote(part) for part in scp_command))
    print("SSH command:")
    print(" ".join(shlex.quote(part) for part in ssh_command))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
