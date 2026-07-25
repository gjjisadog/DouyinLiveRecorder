"""Docker release helpers."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from client.version import APP_VERSION

DEFAULT_IMAGE_REPOSITORY = "ghcr.io/gjjisadog/douyin-live-recorder"
DEFAULT_REMOTE_IMAGE_REPOSITORY = DEFAULT_IMAGE_REPOSITORY
DEFAULT_PLATFORMS = ("linux/amd64", "linux/arm64")
DEFAULT_TARGET = "daemon"
DOCKER_TARGETS = ("daemon", "nas-web")


def default_image_tag() -> str:
    return APP_VERSION


def normalize_repository(repository: str) -> str:
    return repository.strip().strip("/")


def docker_tags(repository: str, include_latest: bool = True) -> list[str]:
    normalized_repository = normalize_repository(repository)
    tags = [f"{normalized_repository}:{default_image_tag()}"]
    if include_latest:
        tags.append(f"{normalized_repository}:latest")
    return tags


def buildx_command(
    repository: str,
    repo_root: Path,
    platforms: tuple[str, ...] = DEFAULT_PLATFORMS,
    push: bool = False,
    include_latest: bool = True,
    target: str = DEFAULT_TARGET,
) -> list[str]:
    if target not in DOCKER_TARGETS:
        raise ValueError(f"Unsupported Docker target: {target}")
    resolved_platforms = platforms if push or len(platforms) <= 1 else (platforms[0],)
    command = [
        "docker",
        "buildx",
        "build",
        "--platform",
        ",".join(resolved_platforms),
        "--file",
        str((repo_root / "Dockerfile").resolve()),
        "--target",
        target,
    ]
    for tag in docker_tags(repository, include_latest=include_latest):
        command.extend(["--tag", tag])
    command.append("--push" if push else "--load")
    command.append(str(repo_root.resolve()))
    return command


def compose_env(repository: str = DEFAULT_IMAGE_REPOSITORY) -> dict[str, str]:
    return {
        "DLR_IMAGE_REPOSITORY": normalize_repository(repository),
        "DLR_IMAGE_TAG": default_image_tag(),
    }


def write_github_output(
    output_path: Path,
    repository: str,
    platforms: tuple[str, ...] = DEFAULT_PLATFORMS,
    include_latest: bool = True,
) -> Path:
    tags = docker_tags(repository, include_latest=include_latest)
    payload = [
        f"image_repository={normalize_repository(repository)}",
        f"image_tag={default_image_tag()}",
        f"platforms={','.join(platforms)}",
        "tags<<EOF",
        "\n".join(tags),
        "EOF",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(payload) + "\n", encoding="utf-8")
    return output_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Docker release helpers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    version_parser = subparsers.add_parser("print-version", help="Print the default Docker image tag.")
    version_parser.set_defaults(command_name="print-version")

    env_parser = subparsers.add_parser("print-compose-env", help="Print compose env variables.")
    env_parser.add_argument("--repository", default=DEFAULT_IMAGE_REPOSITORY)
    env_parser.set_defaults(command_name="print-compose-env")

    tags_parser = subparsers.add_parser("print-tags", help="Print resolved Docker image tags.")
    tags_parser.add_argument("--repository", default=DEFAULT_REMOTE_IMAGE_REPOSITORY)
    tags_parser.add_argument("--no-latest", action="store_true")
    tags_parser.set_defaults(command_name="print-tags")

    output_parser = subparsers.add_parser("github-output", help="Write GitHub Actions outputs for Docker tags.")
    output_parser.add_argument("--repository", default=DEFAULT_REMOTE_IMAGE_REPOSITORY)
    output_parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT", ""))
    output_parser.add_argument("--no-latest", action="store_true")
    output_parser.set_defaults(command_name="github-output")

    buildx_parser = subparsers.add_parser("buildx", help="Build a multi-arch Docker image with buildx.")
    buildx_parser.add_argument("--repository", default=DEFAULT_IMAGE_REPOSITORY)
    buildx_parser.add_argument("--repo-root", default=".")
    buildx_parser.add_argument("--platforms", default=",".join(DEFAULT_PLATFORMS))
    buildx_parser.add_argument("--push", action="store_true")
    buildx_parser.add_argument("--target", choices=DOCKER_TARGETS, default=DEFAULT_TARGET)
    buildx_parser.add_argument("--dry-run", action="store_true")
    buildx_parser.add_argument("--no-latest", action="store_true")
    buildx_parser.set_defaults(command_name="buildx")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command_name == "print-version":
        print(default_image_tag())
        return 0

    if args.command_name == "print-compose-env":
        for key, value in compose_env(args.repository).items():
            print(f"{key}={value}")
        return 0

    if args.command_name == "print-tags":
        print("\n".join(docker_tags(args.repository, include_latest=not args.no_latest)))
        return 0

    if args.command_name == "github-output":
        if not args.github_output:
            raise SystemExit("Missing --github-output path.")
        output_path = Path(args.github_output).resolve()
        write_github_output(
            output_path=output_path,
            repository=args.repository,
            include_latest=not args.no_latest,
        )
        return 0

    repo_root = Path(args.repo_root).resolve()
    platforms = tuple(item.strip() for item in args.platforms.split(",") if item.strip())
    command = buildx_command(
        repository=args.repository,
        repo_root=repo_root,
        platforms=platforms,
        push=args.push,
        include_latest=not args.no_latest,
        target=args.target,
    )
    print(" ".join(command))
    if not args.dry_run:
        subprocess.run(command, check=True, cwd=repo_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
