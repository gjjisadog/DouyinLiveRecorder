from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


class LegacyLoggerWindowedTests(unittest.TestCase):
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
