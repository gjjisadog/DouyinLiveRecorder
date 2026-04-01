from __future__ import annotations

import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from client.infra.docker.healthcheck import (
    is_recorder_process_running,
    read_url_entries,
    run_healthcheck,
)


class DockerHealthcheckTests(unittest.TestCase):
    def make_workspace(self, prefix: str) -> Path:
        root = Path.cwd() / f"{prefix}_{uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def write_cmdline(self, proc_root: Path, pid: str, *parts: str) -> None:
        proc_dir = proc_root / pid
        proc_dir.mkdir(parents=True, exist_ok=True)
        (proc_dir / "cmdline").write_bytes("\x00".join(parts).encode("utf-8"))

    def test_read_url_entries_skips_blank_and_commented_lines(self) -> None:
        root = self.make_workspace("tmp_docker_healthcheck_urls")
        config_path = root / "URL_config.ini"
        config_path.write_text(
            "# disabled\n\nhttps://live.example.com/a\n  # still disabled\n超清,https://live.example.com/b\n",
            encoding="utf-8-sig",
        )

        entries = read_url_entries(config_path)

        self.assertEqual(
            ["https://live.example.com/a", "超清,https://live.example.com/b"],
            entries,
        )

    def test_run_healthcheck_fails_when_url_config_is_missing(self) -> None:
        root = self.make_workspace("tmp_docker_healthcheck_missing_config")
        proc_root = root / "proc"
        proc_root.mkdir(parents=True, exist_ok=True)
        self.write_cmdline(proc_root, "100", "python", "main.py")

        healthy, message = run_healthcheck(app_root=root, proc_root=proc_root)

        self.assertFalse(healthy)
        self.assertIn("URL config missing or empty", message)

    def test_run_healthcheck_fails_when_recorder_process_is_missing(self) -> None:
        root = self.make_workspace("tmp_docker_healthcheck_missing_process")
        proc_root = root / "proc"
        proc_root.mkdir(parents=True, exist_ok=True)
        config_dir = root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "URL_config.ini").write_text("https://live.example.com/a\n", encoding="utf-8-sig")

        healthy, message = run_healthcheck(app_root=root, proc_root=proc_root)

        self.assertFalse(healthy)
        self.assertIn("recorder process not running", message)

    def test_is_recorder_process_running_matches_python_main_process(self) -> None:
        root = self.make_workspace("tmp_docker_healthcheck_process_scan")
        proc_root = root / "proc"
        proc_root.mkdir(parents=True, exist_ok=True)
        self.write_cmdline(proc_root, "101", "python", "main.py")
        self.write_cmdline(proc_root, "102", "python", "other.py")

        self.assertTrue(is_recorder_process_running(proc_root))

    def test_run_healthcheck_passes_when_config_exists_and_process_is_running(self) -> None:
        root = self.make_workspace("tmp_docker_healthcheck_ok")
        proc_root = root / "proc"
        proc_root.mkdir(parents=True, exist_ok=True)
        config_dir = root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "URL_config.ini").write_text("https://live.example.com/a\n", encoding="utf-8-sig")
        self.write_cmdline(proc_root, "200", "python", "main.py")

        healthy, message = run_healthcheck(app_root=root, proc_root=proc_root)

        self.assertTrue(healthy)
        self.assertIn("recorder healthy", message)


if __name__ == "__main__":
    unittest.main()
