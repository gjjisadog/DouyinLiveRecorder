from __future__ import annotations

import shutil
import tarfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from client.infra.docker.flyinnas_deploy import (
    DeployTarget,
    build_scp_command,
    build_ssh_command,
    bundle_basename,
    create_deploy_bundle,
    deploy_over_ssh,
    normalize_remote_dir,
    render_remote_script,
    run_command,
)


class FlyInNasDeployTests(unittest.TestCase):
    def make_workspace(self, prefix: str) -> Path:
        root = Path.cwd() / f"{prefix}_{uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def prepare_repo_root(self) -> Path:
        root = self.make_workspace("tmp_flyinnas_deploy")
        (root / "client" / "infra" / "docker").mkdir(parents=True, exist_ok=True)
        (root / "config").mkdir(parents=True, exist_ok=True)
        (root / "dist").mkdir(parents=True, exist_ok=True)
        (root / "logs").mkdir(parents=True, exist_ok=True)
        (root / "downloads").mkdir(parents=True, exist_ok=True)
        (root / "backup_config").mkdir(parents=True, exist_ok=True)
        (root / ".client-conda-env").mkdir(parents=True, exist_ok=True)
        (root / "docker-compose.flyinnas.yaml").write_text("services:\n", encoding="utf-8")
        (root / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
        (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (root / "config" / "config.ini").write_text("[录制设置]\n", encoding="utf-8")
        (root / "config" / "URL_config.ini").write_text("https://live.douyin.com/123\n", encoding="utf-8")
        (root / "config" / "douyin.yaml").write_text(
            "rooms:\n  - url: https://live.douyin.com/123\n",
            encoding="utf-8",
        )
        (root / "dist" / "ignore.txt").write_text("ignore\n", encoding="utf-8")
        (root / "logs" / "ignore.log").write_text("ignore\n", encoding="utf-8")
        (root / ".client-conda-env" / "ignore.txt").write_text("ignore\n", encoding="utf-8")
        return root

    def test_normalize_remote_dir_trims_trailing_slash(self) -> None:
        self.assertEqual("/vol1/docker/app", normalize_remote_dir("/vol1/docker/app/"))

    def test_bundle_basename_contains_version(self) -> None:
        self.assertEqual("douyin-live-recorder-flyinnas-4.0.7.tar.gz", bundle_basename("4.0.7"))

    def test_create_deploy_bundle_keeps_app_files_and_templates(self) -> None:
        repo_root = self.prepare_repo_root()
        bundle_path = repo_root / "bundle.tar.gz"

        create_deploy_bundle(repo_root, bundle_path)

        self.assertTrue(bundle_path.exists())
        with tarfile.open(bundle_path, "r:gz") as archive:
            names = sorted(archive.getnames())
        self.assertIn("app/docker-compose.flyinnas.yaml", names)
        self.assertIn("app/Dockerfile", names)
        self.assertIn("app/main.py", names)
        self.assertNotIn("config_templates/config.ini", names)
        self.assertNotIn("config_templates/URL_config.ini", names)
        self.assertIn("config_templates/douyin.yaml", names)
        self.assertNotIn("app/dist/ignore.txt", names)
        self.assertNotIn("app/logs/ignore.log", names)
        self.assertNotIn("app/.client-conda-env/ignore.txt", names)

    def test_build_scp_and_ssh_commands_include_port_identity_and_destination(self) -> None:
        target = DeployTarget(host="192.168.1.10", user="admin", port=2222, identity_file=Path("C:/keys/id_ed25519"))

        scp_command = build_scp_command(Path("bundle.tar.gz"), target, "/tmp/bundle.tar.gz")
        ssh_command = build_ssh_command(target, ["echo", "hello"])

        self.assertEqual(
            ["scp", "-P", "2222", "-i", str(target.identity_file), "bundle.tar.gz", "admin@192.168.1.10:/tmp/bundle.tar.gz"],
            scp_command,
        )
        self.assertEqual(["ssh", "-p", "2222", "-i", str(target.identity_file), "admin@192.168.1.10", "echo", "hello"], ssh_command)

    def test_render_remote_script_handles_expected_tag_and_regression(self) -> None:
        script = render_remote_script()

        self.assertIn('docker compose -f "$APP_ROOT/docker-compose.flyinnas.yaml" up -d --build', script)
        self.assertIn('upsert_env_key "$ENV_FILE" "DLR_IMAGE_TAG" "$EXPECTED_TAG"', script)
        self.assertIn('"$APP_ROOT/config/douyin.yaml"', script)
        self.assertIn('"$APP_ROOT/client_data/secrets/web_token"', script)
        self.assertIn('"$REMOTE_PYTHON" -m client.infra.docker.flyinnas_regression "$SCENARIO"', script)

    def test_deploy_over_ssh_dry_run_returns_commands(self) -> None:
        repo_root = self.prepare_repo_root()
        target = DeployTarget(host="nas.local", user="wxw", port=22)

        scp_command, ssh_command = deploy_over_ssh(
            repo_root=repo_root,
            target=target,
            remote_dir="/vol1/docker/douyin-live-recorder",
            scenario="upgrade-deploy",
            remote_python="python3",
            expected_tag="4.0.7",
            image_repository="douyin-live-recorder",
            dry_run=True,
        )

        self.assertEqual("scp", scp_command[0])
        self.assertTrue(scp_command[-1].startswith("wxw@nas.local:/tmp/douyin-live-recorder-flyinnas-4.0.7.tar.gz"))
        self.assertEqual("ssh", ssh_command[0])
        self.assertIn("wxw@nas.local", ssh_command)
        self.assertEqual(
            [
                "sh",
                "-s",
                "--",
                "/vol1/docker/douyin-live-recorder",
                "/tmp/douyin-live-recorder-flyinnas-4.0.7.tar.gz",
                "upgrade-deploy",
                "python3",
                "4.0.7",
                "douyin-live-recorder",
            ],
            ssh_command[-9:],
        )

    def test_run_command_sends_utf8_bytes_with_lf_when_input_present(self) -> None:
        captured_kwargs = {}

        def fake_run(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return None

        with patch("client.infra.docker.flyinnas_deploy.subprocess.run", side_effect=fake_run):
            run_command(["ssh", "host"], input_text="#!/bin/sh\nset -eu\n")

        self.assertEqual(b"#!/bin/sh\nset -eu\n", captured_kwargs["input"])
        self.assertFalse(captured_kwargs["text"])


if __name__ == "__main__":
    unittest.main()
