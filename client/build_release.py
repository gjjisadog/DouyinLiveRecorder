"""Build helpers for packaging the desktop client."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
import zipfile

from client.version import APP_NAME, APP_VERSION, COMPANY_NAME, PRODUCT_NAME, windows_file_version


@dataclass(slots=True)
class ReleasePaths:
    repo_root: Path
    entry_script: Path
    resources_dir: Path
    dist_dir: Path
    work_dir: Path
    spec_dir: Path
    version_file: Path
    icon_svg_path: Path
    icon_ico_path: Path
    app_dist_dir: Path
    release_archive: Path
    release_checksums: Path
    release_manifest_json: Path
    release_manifest_md: Path


@dataclass(slots=True)
class ReleaseArtifacts:
    archive_path: Path
    checksum_path: Path
    manifest_json_path: Path
    manifest_md_path: Path


@dataclass(slots=True)
class BuildReleaseResult:
    command: list[str]
    artifacts: ReleaseArtifacts | None = None


def release_package_basename() -> str:
    normalized_name = re.sub(r"[^A-Za-z0-9]+", "-", APP_NAME).strip("-")
    return f"{normalized_name}-{APP_VERSION}-windows-x64"


def default_release_paths(repo_root: Path | None = None) -> ReleasePaths:
    root = (repo_root or Path(__file__).resolve().parent.parent).resolve()
    client_dir = root / "client"
    build_root = root / "build" / "client-release"
    dist_dir = root / "dist"
    package_basename = release_package_basename()
    return ReleasePaths(
        repo_root=root,
        entry_script=client_dir / "main.py",
        resources_dir=client_dir / "resources",
        dist_dir=dist_dir,
        work_dir=build_root / "work",
        spec_dir=build_root / "spec",
        version_file=build_root / "windows-version-info.txt",
        icon_svg_path=client_dir / "resources" / "app_icon.svg",
        icon_ico_path=client_dir / "resources" / "app_icon.ico",
        app_dist_dir=dist_dir / APP_NAME,
        release_archive=dist_dir / f"{package_basename}.zip",
        release_checksums=dist_dir / f"{package_basename}.sha256",
        release_manifest_json=dist_dir / f"{package_basename}.manifest.json",
        release_manifest_md=dist_dir / f"{package_basename}.manifest.md",
    )


def build_windows_version_info() -> str:
    version = windows_file_version()
    return "\n".join(
        [
            "VSVersionInfo(",
            "  ffi=FixedFileInfo(",
            f"    filevers=({version}),",
            f"    prodvers=({version}),",
            "    mask=0x3F,",
            "    flags=0x0,",
            "    OS=0x40004,",
            "    fileType=0x1,",
            "    subtype=0x0,",
            "    date=(0, 0)",
            "  ),",
            "  kids=[",
            "    StringFileInfo([",
            "      StringTable(",
            "        '040904B0',",
            "        [",
            f"          StringStruct('CompanyName', '{COMPANY_NAME}'),",
            f"          StringStruct('FileDescription', '{PRODUCT_NAME}'),",
            f"          StringStruct('FileVersion', '{APP_VERSION}'),",
            f"          StringStruct('InternalName', '{APP_NAME}'),",
            f"          StringStruct('OriginalFilename', '{APP_NAME}.exe'),",
            f"          StringStruct('ProductName', '{PRODUCT_NAME}'),",
            f"          StringStruct('ProductVersion', '{APP_VERSION}')",
            "        ]",
            "      )",
            "    ]),",
            "    VarFileInfo([VarStruct('Translation', [1033, 1200])])",
            "  ]",
            ")",
            "",
        ]
    )


def write_windows_version_file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_windows_version_info(), encoding="utf-8")
    return path


def discover_additional_binaries(python_executable: Path) -> list[str]:
    env_root = python_executable.resolve().parent
    library_bin_dir = env_root / "Library" / "bin"
    if not library_bin_dir.exists():
        return []
    return [f"{binary_path}{os.pathsep}." for binary_path in sorted(library_bin_dir.glob("*.dll"))]


def build_pyinstaller_command(python_executable: Path, paths: ReleasePaths) -> list[str]:
    paths.dist_dir.mkdir(parents=True, exist_ok=True)
    paths.work_dir.mkdir(parents=True, exist_ok=True)
    paths.spec_dir.mkdir(parents=True, exist_ok=True)

    command = [
        str(python_executable),
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(paths.dist_dir),
        "--workpath",
        str(paths.work_dir),
        "--specpath",
        str(paths.spec_dir),
        "--hidden-import",
        "PySide6.QtSvg",
        "--add-data",
        f"{paths.resources_dir}{os.pathsep}client/resources",
        str(paths.entry_script),
    ]
    for binary_mapping in discover_additional_binaries(python_executable):
        command.extend(["--add-binary", binary_mapping])
    if os.name == "nt":
        command.extend(["--version-file", str(paths.version_file)])
        if paths.icon_ico_path.exists():
            command.extend(["--icon", str(paths.icon_ico_path)])
    return command


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def collect_release_files(root_dir: Path) -> list[dict[str, int | str]]:
    files: list[dict[str, int | str]] = []
    for file_path in sorted(path for path in root_dir.rglob("*") if path.is_file()):
        files.append(
            {
                "path": file_path.relative_to(root_dir).as_posix(),
                "size": file_path.stat().st_size,
            }
        )
    return files


def create_release_archive(paths: ReleasePaths) -> Path:
    if not paths.app_dist_dir.exists():
        raise FileNotFoundError(f"Built app directory not found: {paths.app_dist_dir}")
    if paths.release_archive.exists():
        paths.release_archive.unlink()
    with zipfile.ZipFile(paths.release_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file_path in sorted(path for path in paths.app_dist_dir.rglob("*") if path.is_file()):
            archive.write(file_path, arcname=file_path.relative_to(paths.dist_dir))
    return paths.release_archive


def build_release_manifest(paths: ReleasePaths, archive_path: Path) -> dict:
    executable_name = f"{APP_NAME}.exe"
    executable_path = paths.app_dist_dir / executable_name
    packaged_files = collect_release_files(paths.app_dist_dir)
    return {
        "app_name": APP_NAME,
        "product_name": PRODUCT_NAME,
        "version": APP_VERSION,
        "platform": "windows-x64",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dist_dir": paths.app_dist_dir.name,
        "entry_executable": executable_name if executable_path.exists() else "",
        "archive": archive_path.name,
        "artifacts": [],
        "packaged_files": packaged_files,
        "packaged_file_count": len(packaged_files),
        "packaged_total_size": sum(int(item["size"]) for item in packaged_files),
    }


def write_release_manifest(paths: ReleasePaths, manifest: dict) -> tuple[Path, Path]:
    paths.release_manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    packaged_file_count = int(manifest["packaged_file_count"])
    packaged_total_size = int(manifest["packaged_total_size"])
    entry_executable = str(manifest["entry_executable"] or "-")
    lines = [
        f"# {APP_NAME} Release Manifest",
        "",
        f"- Version: `{manifest['version']}`",
        f"- Platform: `{manifest['platform']}`",
        f"- Generated At: `{manifest['generated_at']}`",
        f"- App Directory: `{manifest['dist_dir']}`",
        f"- Entry Executable: `{entry_executable}`",
        f"- Archive: `{manifest['archive']}`",
        f"- Packaged Files: `{packaged_file_count}`",
        f"- Packaged Total Size: `{packaged_total_size}` bytes",
        "",
        "## Packaged Files",
        "",
    ]
    for item in manifest["packaged_files"]:
        lines.append(f"- `{item['path']}` ({item['size']} bytes)")
    lines.append("")
    lines.append("## Release Artifacts")
    lines.append("")
    for item in manifest["artifacts"]:
        lines.append(f"- `{item['path']}` ({item['size']} bytes, sha256 `{item['sha256']}`)")
    lines.append("")
    paths.release_manifest_md.write_text("\n".join(lines), encoding="utf-8")
    return paths.release_manifest_json, paths.release_manifest_md


def write_release_checksums(paths: ReleasePaths, artifact_paths: list[Path]) -> Path:
    lines: list[str] = []
    for artifact_path in artifact_paths:
        lines.append(f"{file_sha256(artifact_path)} *{artifact_path.name}")
    paths.release_checksums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return paths.release_checksums


def package_release(paths: ReleasePaths) -> ReleaseArtifacts:
    archive_path = create_release_archive(paths)
    manifest = build_release_manifest(paths, archive_path)
    executable_path = paths.app_dist_dir / f"{APP_NAME}.exe"
    artifact_paths = [path for path in (archive_path, executable_path) if path.exists()]
    write_release_manifest(paths, manifest)
    artifact_paths.extend([paths.release_manifest_json, paths.release_manifest_md])
    checksum_path = write_release_checksums(paths, artifact_paths)
    artifact_paths.append(checksum_path)
    manifest["artifacts"] = [
        {
            "path": artifact_path.name,
            "size": artifact_path.stat().st_size,
            "sha256": file_sha256(artifact_path),
        }
        for artifact_path in artifact_paths
    ]
    write_release_manifest(paths, manifest)
    return ReleaseArtifacts(
        archive_path=archive_path,
        checksum_path=checksum_path,
        manifest_json_path=paths.release_manifest_json,
        manifest_md_path=paths.release_manifest_md,
    )


def run_build(
    python_executable: Path,
    repo_root: Path | None = None,
    dry_run: bool = False,
    package_after_build: bool = True,
) -> BuildReleaseResult:
    paths = default_release_paths(repo_root)
    if os.name == "nt":
        write_windows_version_file(paths.version_file)
    command = build_pyinstaller_command(python_executable, paths)
    if not dry_run:
        subprocess.run(command, check=True, cwd=paths.repo_root)
    artifacts = package_release(paths) if package_after_build and not dry_run else None
    return BuildReleaseResult(command=command, artifacts=artifacts)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the desktop client release package.")
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to run PyInstaller.",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Optional repository root override.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved PyInstaller command without executing it.",
    )
    parser.add_argument(
        "--skip-package",
        action="store_true",
        help="Skip generating zip/checksum/manifest artifacts after build.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else None
    result = run_build(
        Path(args.python).resolve(),
        repo_root=repo_root,
        dry_run=args.dry_run,
        package_after_build=not args.skip_package,
    )
    print("PyInstaller command:")
    print(" ".join(result.command))
    if result.artifacts is not None:
        print("Release artifacts:")
        print(f"  zip: {result.artifacts.archive_path}")
        print(f"  sha256: {result.artifacts.checksum_path}")
        print(f"  manifest json: {result.artifacts.manifest_json_path}")
        print(f"  manifest md: {result.artifacts.manifest_md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
