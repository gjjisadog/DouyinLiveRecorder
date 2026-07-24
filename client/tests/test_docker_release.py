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

        self.assertEqual("douyin-live-recorder", payload["DLR_IMAGE_REPOSITORY"])
        self.assertEqual(APP_VERSION, payload["DLR_IMAGE_TAG"])

    def test_docker_tags_include_version_and_latest(self) -> None:
        tags = docker_tags("ihmily/douyin-live-recorder")

        self.assertEqual(
            [
                f"ihmily/douyin-live-recorder:{APP_VERSION}",
                "ihmily/douyin-live-recorder:latest",
            ],
            tags,
        )

    def test_buildx_command_contains_platforms_and_tags(self) -> None:
        root = self.make_workspace("tmp_docker_release_buildx")
        command = buildx_command(
            repository="ihmily/douyin-live-recorder",
            repo_root=root,
            push=True,
        )

        self.assertIn("buildx", command)
        self.assertIn("--platform", command)
        self.assertIn("linux/amd64,linux/arm64", command)
        self.assertIn("--push", command)
        self.assertIn(f"ihmily/douyin-live-recorder:{APP_VERSION}", command)
        self.assertIn("ihmily/douyin-live-recorder:latest", command)

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

        write_github_output(output_path, "ihmily/douyin-live-recorder")

        content = output_path.read_text(encoding="utf-8")
        self.assertIn("image_repository=ihmily/douyin-live-recorder", content)
        self.assertIn(f"image_tag={APP_VERSION}", content)
        self.assertIn("platforms=linux/amd64,linux/arm64", content)
        self.assertIn(f"ihmily/douyin-live-recorder:{APP_VERSION}", content)

    def test_compose_files_reference_default_version_tag(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        expected = f"${{DLR_IMAGE_REPOSITORY:-douyin-live-recorder}}:${{DLR_IMAGE_TAG:-{APP_VERSION}}}"
        for relative_path in ("docker-compose.yaml", "docker-compose.flyinnas.yaml", ".env.docker.example"):
            content = (repo_root / relative_path).read_text(encoding="utf-8")
            self.assertIn(APP_VERSION, content)
            if relative_path.endswith(".yaml"):
                self.assertIn(expected, content)
                if relative_path == "docker-compose.yaml":
                    self.assertIn("DOUYIN_CONFIG", content)
                    self.assertNotIn("DLR_WEB_PORT", content)
                else:
                    self.assertIn("DLR_WEB_PORT", content)
            else:
                self.assertIn("DLR_WEB_PORT=18091", content)

    def test_flyinnas_import_compose_uses_fixed_image_and_port(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        content = (repo_root / "docker-compose.flyinnas.import.yaml").read_text(encoding="utf-8")

        self.assertIn(f"image: douyin-live-recorder:{APP_VERSION}-fnos-webui", content)
        self.assertIn('- "18091:18091"', content)
        self.assertNotIn("build:", content)

    def test_github_workflow_publishes_edge_and_release_tags(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        content = (repo_root / ".github" / "workflows" / "build-image.yml").read_text(encoding="utf-8")

        self.assertIn("docker/metadata-action@v5", content)
        self.assertIn("type=raw,value=edge", content)
        self.assertIn("type=raw,value=latest", content)
        self.assertIn("linux/amd64,linux/arm64", content)
        self.assertIn("sbom: true", content)


if __name__ == "__main__":
    unittest.main()
