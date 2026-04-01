from __future__ import annotations

import shutil
import unittest
from pathlib import Path
from uuid import uuid4
import zipfile

from client.build_release import (
    build_release_manifest,
    build_pyinstaller_command,
    build_windows_version_info,
    create_release_archive,
    discover_additional_binaries,
    default_release_paths,
    package_release,
    release_package_basename,
    write_windows_version_file,
)


class BuildReleaseTests(unittest.TestCase):
    def make_workspace(self, prefix: str) -> Path:
        root = Path.cwd() / f"{prefix}_{uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def test_default_release_paths_points_to_expected_locations(self) -> None:
        root = self.make_workspace("tmp_release_paths")

        paths = default_release_paths(root)

        self.assertEqual(root / "client" / "main.py", paths.entry_script)
        self.assertEqual(root / "client" / "resources", paths.resources_dir)
        self.assertEqual(root / "dist", paths.dist_dir)
        self.assertEqual(root / "dist" / "DouyinLiveRecorder Client", paths.app_dist_dir)
        self.assertEqual(root / "dist" / "DouyinLiveRecorder-Client-4.0.7-windows-x64.zip", paths.release_archive)
        self.assertEqual(root / "build" / "client-release" / "windows-version-info.txt", paths.version_file)

    def test_build_windows_version_info_contains_product_metadata(self) -> None:
        content = build_windows_version_info()

        self.assertIn("StringStruct('CompanyName', 'DouyinLiveRecorder')", content)
        self.assertIn("StringStruct('ProductName', 'DouyinLiveRecorder Client')", content)
        self.assertIn("StringStruct('ProductVersion', '4.0.7')", content)

    def test_build_pyinstaller_command_includes_release_arguments(self) -> None:
        root = self.make_workspace("tmp_release_command")
        paths = default_release_paths(root)
        paths.entry_script.parent.mkdir(parents=True, exist_ok=True)
        paths.resources_dir.mkdir(parents=True, exist_ok=True)
        paths.version_file.parent.mkdir(parents=True, exist_ok=True)

        command = build_pyinstaller_command(Path("C:/Python311/python.exe"), paths)

        self.assertIn("-m", command)
        self.assertIn("PyInstaller", command)
        self.assertIn("--windowed", command)
        self.assertIn("--version-file", command)
        self.assertIn("--hidden-import", command)
        self.assertIn("PySide6.QtSvg", command)
        self.assertIn(str(paths.entry_script), command)
        self.assertIn(f"{paths.resources_dir};client/resources", command)
        self.assertNotIn("--icon", command)

    def test_build_pyinstaller_command_uses_icon_when_ico_exists(self) -> None:
        root = self.make_workspace("tmp_release_icon")
        paths = default_release_paths(root)
        paths.entry_script.parent.mkdir(parents=True, exist_ok=True)
        paths.resources_dir.mkdir(parents=True, exist_ok=True)
        paths.icon_ico_path.write_bytes(b"ico")

        command = build_pyinstaller_command(Path("C:/Python311/python.exe"), paths)

        self.assertIn("--icon", command)
        self.assertIn(str(paths.icon_ico_path), command)

    def test_discover_additional_binaries_collects_conda_library_bin_dlls(self) -> None:
        root = self.make_workspace("tmp_release_binaries")
        python_executable = root / "python.exe"
        library_bin_dir = root / "Library" / "bin"
        library_bin_dir.mkdir(parents=True, exist_ok=True)
        dll_path = library_bin_dir / "Qt6Core.dll"
        dll_path.write_bytes(b"dll")

        mappings = discover_additional_binaries(python_executable)

        self.assertEqual([f"{dll_path};."], mappings)

    def test_write_windows_version_file_creates_target_file(self) -> None:
        root = self.make_workspace("tmp_release_version_file")
        target = root / "build" / "windows-version-info.txt"

        write_windows_version_file(target)

        self.assertTrue(target.exists())
        self.assertIn("VSVersionInfo(", target.read_text(encoding="utf-8"))

    def test_release_package_basename_uses_versioned_windows_name(self) -> None:
        self.assertEqual("DouyinLiveRecorder-Client-4.0.7-windows-x64", release_package_basename())

    def test_create_release_archive_preserves_app_directory_root(self) -> None:
        root = self.make_workspace("tmp_release_archive")
        paths = default_release_paths(root)
        app_dir = paths.app_dist_dir
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "DouyinLiveRecorder Client.exe").write_bytes(b"exe")
        (app_dir / "client_data" / "config.json").parent.mkdir(parents=True, exist_ok=True)
        (app_dir / "client_data" / "config.json").write_text("{}", encoding="utf-8")

        archive_path = create_release_archive(paths)

        self.assertTrue(archive_path.exists())
        with zipfile.ZipFile(archive_path) as archive:
            names = sorted(archive.namelist())
        self.assertIn("DouyinLiveRecorder Client/DouyinLiveRecorder Client.exe", names)
        self.assertIn("DouyinLiveRecorder Client/client_data/config.json", names)

    def test_build_release_manifest_includes_packaged_files(self) -> None:
        root = self.make_workspace("tmp_release_manifest")
        paths = default_release_paths(root)
        app_dir = paths.app_dist_dir
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "DouyinLiveRecorder Client.exe").write_bytes(b"exe")
        (app_dir / "README.txt").write_text("hello", encoding="utf-8")

        manifest = build_release_manifest(paths, paths.release_archive)

        self.assertEqual("4.0.7", manifest["version"])
        self.assertEqual("windows-x64", manifest["platform"])
        self.assertEqual("DouyinLiveRecorder Client.exe", manifest["entry_executable"])
        self.assertEqual(2, manifest["packaged_file_count"])
        self.assertEqual(
            ["DouyinLiveRecorder Client.exe", "README.txt"],
            [item["path"] for item in manifest["packaged_files"]],
        )

    def test_package_release_writes_zip_checksum_and_manifest_files(self) -> None:
        root = self.make_workspace("tmp_release_package")
        paths = default_release_paths(root)
        app_dir = paths.app_dist_dir
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "DouyinLiveRecorder Client.exe").write_bytes(b"exe-binary")
        (app_dir / "resources" / "app_icon.svg").parent.mkdir(parents=True, exist_ok=True)
        (app_dir / "resources" / "app_icon.svg").write_text("<svg />", encoding="utf-8")

        artifacts = package_release(paths)

        self.assertTrue(artifacts.archive_path.exists())
        self.assertTrue(artifacts.checksum_path.exists())
        self.assertTrue(artifacts.manifest_json_path.exists())
        self.assertTrue(artifacts.manifest_md_path.exists())
        checksum_text = artifacts.checksum_path.read_text(encoding="utf-8")
        self.assertIn(paths.release_archive.name, checksum_text)
        self.assertIn(paths.release_manifest_json.name, checksum_text)
        manifest_json = artifacts.manifest_json_path.read_text(encoding="utf-8")
        self.assertIn('"archive": "DouyinLiveRecorder-Client-4.0.7-windows-x64.zip"', manifest_json)
        self.assertIn('"path": "DouyinLiveRecorder Client.exe"', manifest_json)
        manifest_md = artifacts.manifest_md_path.read_text(encoding="utf-8")
        self.assertIn("# DouyinLiveRecorder Client Release Manifest", manifest_md)
        self.assertIn("DouyinLiveRecorder Client.exe", manifest_md)


if __name__ == "__main__":
    unittest.main()
