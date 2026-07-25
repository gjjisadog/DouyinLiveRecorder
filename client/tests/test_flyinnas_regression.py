from __future__ import annotations

import os
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from client.infra.docker.flyinnas_regression import CommandResult, parse_health_status, run_regression


class _FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], CommandResult]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, command: list[str], cwd: Path | None = None) -> CommandResult:
        _ = cwd
        key = tuple(command)
        self.calls.append(key)
        return self.responses.get(key, CommandResult(returncode=1, stderr=f"unexpected command: {' '.join(command)}"))


class FlyInNasRegressionTests(unittest.TestCase):
    def make_workspace(self, prefix: str) -> Path:
        root = Path.cwd() / f"{prefix}_{uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def prepare_app_root(self) -> Path:
        root = self.make_workspace("tmp_flyinnas_regression")
        for relative in ("config", "logs", "backup_config", "downloads"):
            (root / relative).mkdir(parents=True, exist_ok=True)
        (root / "config" / "config.ini").write_text("[录制设置]\n", encoding="utf-8")
        (root / "config" / "URL_config.ini").write_text("https://live.douyin.com/123\n", encoding="utf-8")
        (root / "docker-compose.flyinnas.yaml").write_text("services:\n  douyin-live-recorder:\n    image: demo:4.0.7\n", encoding="utf-8")
        return root

    def test_parse_health_status_supports_json_and_plain_text(self) -> None:
        self.assertEqual("healthy", parse_health_status('{"Status":"healthy"}'))
        self.assertEqual("healthy", parse_health_status("healthy"))
        self.assertEqual("", parse_health_status(""))

    def test_run_regression_passes_for_first_deploy(self) -> None:
        root = self.prepare_app_root()
        compose_file = root / "docker-compose.flyinnas.yaml"
        runner = _FakeRunner(
            {
                ("docker", "--version"): CommandResult(0, "Docker version 28.0.0"),
                ("docker", "compose", "version"): CommandResult(0, "Docker Compose version v2.35.0"),
                ("docker", "compose", "-f", str(compose_file), "config"): CommandResult(0, "services: {}"),
                ("docker", "inspect", "--format={{.State.Status}}", "douyin-live-recorder"): CommandResult(0, "running"),
                ("docker", "inspect", "--format={{json .State.Health}}", "douyin-live-recorder"): CommandResult(
                    0, '{"Status":"healthy"}'
                ),
                ("docker", "inspect", "--format={{.Config.Image}}", "douyin-live-recorder"): CommandResult(
                    0, "douyin-live-recorder:4.0.7"
                ),
                ("docker", "compose", "-f", str(compose_file), "logs", "--tail=200"): CommandResult(
                    0, "startup ok\nmonitoring tasks\n"
                ),
            }
        )

        report = run_regression("first-deploy", app_root=root, runner=runner)

        self.assertTrue(report.ok)
        self.assertTrue(all(check.ok for check in report.checks))

    def test_run_regression_fails_when_url_config_is_empty(self) -> None:
        root = self.prepare_app_root()
        (root / "config" / "URL_config.ini").write_text("", encoding="utf-8")
        compose_file = root / "docker-compose.flyinnas.yaml"
        runner = _FakeRunner(
            {
                ("docker", "--version"): CommandResult(0, "Docker version 28.0.0"),
                ("docker", "compose", "version"): CommandResult(0, "Docker Compose version v2.35.0"),
                ("docker", "compose", "-f", str(compose_file), "config"): CommandResult(0, "services: {}"),
                ("docker", "inspect", "--format={{.State.Status}}", "douyin-live-recorder"): CommandResult(0, "running"),
                ("docker", "inspect", "--format={{json .State.Health}}", "douyin-live-recorder"): CommandResult(
                    0, '{"Status":"healthy"}'
                ),
                ("docker", "inspect", "--format={{.Config.Image}}", "douyin-live-recorder"): CommandResult(
                    0, "douyin-live-recorder:4.0.7"
                ),
                ("docker", "compose", "-f", str(compose_file), "logs", "--tail=200"): CommandResult(
                    0, "startup ok\n"
                ),
            }
        )

        report = run_regression("first-deploy", app_root=root, runner=runner)

        self.assertFalse(report.ok)
        url_check = next(check for check in report.checks if check.name == "url_config_entries")
        self.assertFalse(url_check.ok)

    def test_run_regression_checks_expected_tag_for_upgrade(self) -> None:
        root = self.prepare_app_root()
        compose_file = root / "docker-compose.flyinnas.yaml"
        runner = _FakeRunner(
            {
                ("docker", "--version"): CommandResult(0, "Docker version 28.0.0"),
                ("docker", "compose", "version"): CommandResult(0, "Docker Compose version v2.35.0"),
                ("docker", "compose", "-f", str(compose_file), "config"): CommandResult(0, "services: {}"),
                ("docker", "inspect", "--format={{.State.Status}}", "douyin-live-recorder"): CommandResult(0, "running"),
                ("docker", "inspect", "--format={{json .State.Health}}", "douyin-live-recorder"): CommandResult(
                    0, '{"Status":"healthy"}'
                ),
                ("docker", "inspect", "--format={{.Config.Image}}", "douyin-live-recorder"): CommandResult(
                    0, "douyin-live-recorder:4.0.6"
                ),
                ("docker", "compose", "-f", str(compose_file), "logs", "--tail=200"): CommandResult(
                    0, "startup ok\n"
                ),
            }
        )

        report = run_regression("upgrade-deploy", app_root=root, expected_tag="4.0.7", runner=runner)

        self.assertFalse(report.ok)
        image_check = next(check for check in report.checks if check.name == "container_image")
        self.assertFalse(image_check.ok)
        self.assertIn("expected_tag=4.0.7", image_check.detail)

    def test_run_regression_fails_when_logs_contain_known_startup_error(self) -> None:
        root = self.prepare_app_root()
        compose_file = root / "docker-compose.flyinnas.yaml"
        runner = _FakeRunner(
            {
                ("docker", "--version"): CommandResult(0, "Docker version 28.0.0"),
                ("docker", "compose", "version"): CommandResult(0, "Docker Compose version v2.35.0"),
                ("docker", "compose", "-f", str(compose_file), "config"): CommandResult(0, "services: {}"),
                ("docker", "inspect", "--format={{.State.Status}}", "douyin-live-recorder"): CommandResult(0, "running"),
                ("docker", "inspect", "--format={{json .State.Health}}", "douyin-live-recorder"): CommandResult(
                    0, '{"Status":"healthy"}'
                ),
                ("docker", "inspect", "--format={{.Config.Image}}", "douyin-live-recorder"): CommandResult(
                    0, "douyin-live-recorder:4.0.7"
                ),
                ("docker", "compose", "-f", str(compose_file), "logs", "--tail=200"): CommandResult(
                    0, "ModuleNotFoundError: No module named 'foo'\n"
                ),
            }
        )

        report = run_regression("rollback-deploy", app_root=root, runner=runner)

        self.assertFalse(report.ok)
        logs_check = next(check for check in report.checks if check.name == "recent_logs")
        self.assertFalse(logs_check.ok)
        self.assertIn("ModuleNotFoundError", logs_check.detail)


if __name__ == "__main__":
    unittest.main()
