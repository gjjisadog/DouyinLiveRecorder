from __future__ import annotations

import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from client.infra.docker.release import (
    buildx_command,
    compose_env,
    default_image_tag,
    docker_tags,
    write_github_output,
)
from client.version import APP_VERSION


class DockerReleaseTests(unittest.TestCase):
    def make_workspace(self, prefix: str) -> Path:
        root = Path.cwd() / f"{prefix}_{uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def test_default_image_tag_matches_app_version(self) -> None:
        self.assertEqual(APP_VERSION, default_image_tag())

    def test_compose_env_uses_default_app_version(self) -> None:
        payload = compose_env()

        self.assertEqual("ghcr.io/gjjisadog/douyin-live-recorder", payload["DLR_IMAGE_REPOSITORY"])
        self.assertEqual(APP_VERSION, payload["DLR_IMAGE_TAG"])

    def test_docker_tags_include_version_and_latest(self) -> None:
        tags = docker_tags("ghcr.io/gjjisadog/douyin-live-recorder")

        self.assertEqual(
            [
                f"ghcr.io/gjjisadog/douyin-live-recorder:{APP_VERSION}",
                "ghcr.io/gjjisadog/douyin-live-recorder:latest",
            ],
            tags,
        )

    def test_buildx_command_contains_platforms_and_tags(self) -> None:
        root = self.make_workspace("tmp_docker_release_buildx")
        command = buildx_command(
            repository="ghcr.io/gjjisadog/douyin-live-recorder",
            repo_root=root,
            push=True,
        )

        self.assertIn("buildx", command)
        self.assertIn("--platform", command)
        self.assertIn("linux/amd64,linux/arm64", command)
        self.assertIn("--push", command)
        self.assertIn(f"ghcr.io/gjjisadog/douyin-live-recorder:{APP_VERSION}", command)
        self.assertIn("ghcr.io/gjjisadog/douyin-live-recorder:latest", command)
        self.assertEqual("daemon", command[command.index("--target") + 1])

    def test_buildx_command_falls_back_to_single_platform_when_loading_locally(self) -> None:
        root = self.make_workspace("tmp_docker_release_load")

        command = buildx_command(
            repository="douyin-live-recorder",
            repo_root=root,
            push=False,
        )

        platform_index = command.index("--platform") + 1
        self.assertEqual("linux/amd64", command[platform_index])
        self.assertIn("--load", command)

    def test_write_github_output_writes_expected_keys(self) -> None:
        root = self.make_workspace("tmp_docker_release_output")
        output_path = root / "github-output.txt"

        write_github_output(output_path, "ghcr.io/gjjisadog/douyin-live-recorder")

        content = output_path.read_text(encoding="utf-8")
        self.assertIn("image_repository=ghcr.io/gjjisadog/douyin-live-recorder", content)
        self.assertIn(f"image_tag={APP_VERSION}", content)
        self.assertIn("platforms=linux/amd64,linux/arm64", content)
        self.assertIn(f"ghcr.io/gjjisadog/douyin-live-recorder:{APP_VERSION}", content)

    def test_compose_files_reference_default_version_tag(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        expected_repository = "${DLR_IMAGE_REPOSITORY:-ghcr.io/gjjisadog/douyin-live-recorder}"
        for relative_path in ("docker-compose.yaml", "docker-compose.flyinnas.yaml", ".env.docker.example"):
            content = (repo_root / relative_path).read_text(encoding="utf-8")
            self.assertIn(APP_VERSION, content)
            if relative_path.endswith(".yaml"):
                self.assertIn(expected_repository, content)
                if relative_path == "docker-compose.yaml":
                    self.assertIn("DOUYIN_CONFIG", content)
                    self.assertNotIn("DLR_WEB_PORT", content)
                    self.assertIn("target: daemon", content)
                else:
                    self.assertIn("DLR_WEB_PORT", content)
                    self.assertIn("target: nas-web", content)
            else:
                self.assertIn("DLR_WEB_PORT=18091", content)

    def test_flyinnas_import_compose_uses_fixed_image_and_port(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        content = (repo_root / "docker-compose.flyinnas.import.yaml").read_text(encoding="utf-8")

        self.assertIn(f"image: ghcr.io/gjjisadog/douyin-live-recorder:{APP_VERSION}-nas-web", content)
        self.assertIn('- "18091:18091"', content)
        self.assertNotIn("build:", content)
        self.assertIn("stop_grace_period: 90s", content)

    def test_dockerfile_has_explicit_daemon_and_nas_web_contracts(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        content = (repo_root / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("FROM runtime AS daemon", content)
        self.assertIn('CMD ["python", "-m", "app.douyin_daemon"]', content)
        self.assertIn("FROM runtime AS nas-web", content)
        self.assertIn('CMD ["python", "-m", "client.infra.docker.launcher"]', content)
        self.assertIn("https://github.com/gjjisadog/DouyinLiveRecorder", content)

    def test_github_workflow_publishes_edge_and_release_tags(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        content = (repo_root / ".github" / "workflows" / "build-image.yml").read_text(encoding="utf-8")

        self.assertIn("docker/metadata-action@v5", content)
        self.assertIn("type=raw,value=edge", content)
        self.assertIn("type=raw,value=latest", content)
        self.assertIn("linux/amd64,linux/arm64", content)
        self.assertIn("sbom: true", content)
        self.assertIn("python -m pytest -v", content)
        self.assertIn("target: ${{ matrix.target }}", content)
        self.assertIn("ghcr.io/gjjisadog/douyin-live-recorder", content)
        self.assertIn("password: ${{ secrets.GITHUB_TOKEN }}", content)
        self.assertNotIn("DOCKERHUB_", content)
        self.assertIn("docker compose -f docker-compose.flyinnas.import.yaml config", content)
        self.assertIn("docker build --target daemon", content)
        self.assertIn("docker build --target nas-web", content)
        self.assertIn("scripts/docker_runtime_smoke.py", content)


if __name__ == "__main__":
    unittest.main()
