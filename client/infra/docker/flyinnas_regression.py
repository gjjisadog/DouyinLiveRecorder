"""Regression checks for FlyInNAS/NAS Docker deployments."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import subprocess
import sys

from client.infra.docker.healthcheck import read_url_entries

DEFAULT_CONTAINER_NAME = "douyin-live-recorder"
DEFAULT_SCENARIOS = ("first-deploy", "upgrade-deploy", "rollback-deploy")
DEFAULT_LOG_PATTERNS = (
    "URL_config.ini 为空",
    "URL config missing or empty",
    "ModuleNotFoundError",
    "No module named",
    "未检测到 ffmpeg",
    "ffmpeg is not installed",
)


@dataclass(slots=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(slots=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


@dataclass(slots=True)
class RegressionReport:
    scenario: str
    app_root: str
    ok: bool
    checks: list[CheckResult]


def default_runner(command: list[str], cwd: Path | None = None) -> CommandResult:
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        check=False,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


def compose_file_path(app_root: Path) -> Path:
    return app_root / "docker-compose.flyinnas.yaml"


def required_mount_paths(app_root: Path) -> list[Path]:
    return [
        app_root / "config",
        app_root / "logs",
        app_root / "backup_config",
        app_root / "downloads",
    ]


def add_path_check(results: list[CheckResult], path: Path, label: str) -> None:
    results.append(
        CheckResult(
            name=label,
            ok=path.exists(),
            detail=f"exists: {path}" if path.exists() else f"missing: {path}",
        )
    )


def parse_health_status(raw_output: str) -> str:
    normalized = raw_output.strip()
    if not normalized:
        return ""
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError:
        return normalized.strip('"').strip()
    if isinstance(payload, dict):
        return str(payload.get("Status") or "").strip()
    return str(payload).strip()


def command_error_detail(result: CommandResult) -> str:
    output = result.stderr or result.stdout or f"exit={result.returncode}"
    return output.strip()


def run_command_check(
    results: list[CheckResult],
    *,
    name: str,
    command: list[str],
    runner,
    cwd: Path | None = None,
    success_detail: str,
) -> CommandResult | None:
    result = runner(command, cwd)
    if result.returncode != 0:
        results.append(CheckResult(name=name, ok=False, detail=command_error_detail(result)))
        return None
    results.append(CheckResult(name=name, ok=True, detail=success_detail))
    return result


def run_regression(
    scenario: str,
    *,
    app_root: Path,
    container_name: str = DEFAULT_CONTAINER_NAME,
    expected_tag: str = "",
    runner=default_runner,
) -> RegressionReport:
    if scenario not in DEFAULT_SCENARIOS:
        raise ValueError(f"Unsupported scenario: {scenario}")

    root = app_root.resolve()
    results: list[CheckResult] = []
    compose_file = compose_file_path(root)
    url_config = root / "config" / "URL_config.ini"

    add_path_check(results, compose_file, "compose_file")
    add_path_check(results, root / "config" / "config.ini", "config_ini")
    for mount_path in required_mount_paths(root):
        add_path_check(results, mount_path, f"mount:{mount_path.name}")

    entries = read_url_entries(url_config)
    results.append(
        CheckResult(
            name="url_config_entries",
            ok=bool(entries),
            detail=f"{len(entries)} configured target(s)" if entries else f"missing or empty: {url_config}",
        )
    )

    docker_version = run_command_check(
        results,
        name="docker_cli",
        command=["docker", "--version"],
        runner=runner,
        cwd=root,
        success_detail="docker command available",
    )
    if docker_version is None:
        return RegressionReport(scenario=scenario, app_root=str(root), ok=False, checks=results)

    compose_version = run_command_check(
        results,
        name="docker_compose_cli",
        command=["docker", "compose", "version"],
        runner=runner,
        cwd=root,
        success_detail="docker compose command available",
    )
    if compose_version is None:
        return RegressionReport(scenario=scenario, app_root=str(root), ok=False, checks=results)

    compose_config = run_command_check(
        results,
        name="compose_config",
        command=["docker", "compose", "-f", str(compose_file), "config"],
        runner=runner,
        cwd=root,
        success_detail="compose config resolved successfully",
    )
    if compose_config is None:
        return RegressionReport(scenario=scenario, app_root=str(root), ok=False, checks=results)

    status_result = runner(["docker", "inspect", "--format={{.State.Status}}", container_name], root)
    if status_result.returncode != 0:
        results.append(CheckResult("container_state", False, command_error_detail(status_result)))
    else:
        state = status_result.stdout.strip().lower()
        results.append(CheckResult("container_state", state == "running", f"state={state or 'unknown'}"))

    health_result = runner(["docker", "inspect", "--format={{json .State.Health}}", container_name], root)
    if health_result.returncode != 0:
        results.append(CheckResult("container_health", False, command_error_detail(health_result)))
    else:
        health_status = parse_health_status(health_result.stdout).lower()
        results.append(
            CheckResult(
                "container_health",
                health_status == "healthy",
                f"health={health_status or 'unknown'}",
            )
        )

    image_result = runner(["docker", "inspect", "--format={{.Config.Image}}", container_name], root)
    if image_result.returncode != 0:
        results.append(CheckResult("container_image", False, command_error_detail(image_result)))
    else:
        image_name = image_result.stdout.strip()
        if expected_tag:
            ok = image_name.endswith(f":{expected_tag}")
            detail = f"image={image_name or 'unknown'}; expected_tag={expected_tag}"
        else:
            ok = bool(image_name)
            detail = f"image={image_name or 'unknown'}"
        results.append(CheckResult("container_image", ok, detail))

    logs_result = runner(
        ["docker", "compose", "-f", str(compose_file), "logs", "--tail=200"],
        root,
    )
    if logs_result.returncode != 0:
        results.append(CheckResult("recent_logs", False, command_error_detail(logs_result)))
    else:
        log_text = logs_result.stdout
        found_pattern = next((pattern for pattern in DEFAULT_LOG_PATTERNS if pattern in log_text), "")
        detail = "no known startup error patterns found"
        if found_pattern:
            detail = f"found suspicious log pattern: {found_pattern}"
        results.append(CheckResult("recent_logs", not found_pattern, detail))

    return RegressionReport(
        scenario=scenario,
        app_root=str(root),
        ok=all(check.ok for check in results),
        checks=results,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run FlyInNAS deployment regression checks.")
    parser.add_argument("scenario", choices=DEFAULT_SCENARIOS, help="Regression scenario to validate.")
    parser.add_argument(
        "--app-root",
        default=".",
        help="FlyInNAS project root that contains docker-compose.flyinnas.yaml and mounted directories.",
    )
    parser.add_argument(
        "--container-name",
        default=DEFAULT_CONTAINER_NAME,
        help="Docker container name to inspect.",
    )
    parser.add_argument(
        "--expected-tag",
        default="",
        help="Optional Docker image tag expected to be running after upgrade/rollback.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the regression report as JSON.",
    )
    return parser.parse_args(argv)


def format_report(report: RegressionReport) -> str:
    lines = [
        f"Scenario: {report.scenario}",
        f"App Root: {report.app_root}",
        f"Result: {'PASS' if report.ok else 'FAIL'}",
        "",
    ]
    for check in report.checks:
        marker = "PASS" if check.ok else "FAIL"
        lines.append(f"[{marker}] {check.name}: {check.detail}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_regression(
        args.scenario,
        app_root=Path(args.app_root),
        container_name=args.container_name,
        expected_tag=args.expected_tag,
    )
    if args.json:
        payload = asdict(report)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
