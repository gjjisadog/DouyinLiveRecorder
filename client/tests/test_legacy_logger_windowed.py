from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


class LegacyLoggerWindowedTests(unittest.TestCase):
    def test_legacy_entrypoint_handles_sigterm_with_process_group_escalation(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        source = (repo_root / "main.py").read_text(encoding="utf-8")

        self.assertIn("signal.signal(signal.SIGINT, signal_handler)", source)
        self.assertIn("signal.signal(signal.SIGTERM, signal_handler)", source)
        self.assertIn("start_new_session=os.name != \"nt\"", source)
        self.assertIn("stop_ffmpeg_processes()", source)
        self.assertIn("os.killpg(os.getpgid(process.pid), sig)", source)

    def test_import_logger_with_none_stderr(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        script = (
            "import sys; "
            f"sys.path.insert(0, r'{repo_root}'); "
            "sys.stderr = None; "
            "import src.logger; "
            "print('ok')"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repo_root,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            check=False,
        )

        self.assertEqual(0, result.returncode, msg=result.stderr)
        self.assertIn("ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
