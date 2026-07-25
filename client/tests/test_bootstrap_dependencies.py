from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from client.bootstrap import _ensure_runtime_dependencies
from client.core.exceptions import DependencyMissingError
from client.infra.env.dependency_checker import DependencyChecker


class _OkChecker(DependencyChecker):
    def ensure_ffmpeg(self) -> str:
        return "C:/ffmpeg/bin/ffmpeg.exe"


class _MissingChecker(DependencyChecker):
    def ensure_ffmpeg(self) -> str:
        raise DependencyMissingError("未检测到 ffmpeg，请先安装并确保其已加入 PATH。")


class BootstrapDependencyTests(unittest.TestCase):
    def test_startup_dependency_check_passes_when_ffmpeg_exists(self) -> None:
        logs: list[tuple[str, str | None, str | None]] = []

        result = _ensure_runtime_dependencies(
            checker=_OkChecker(),
            prompt_continue=lambda title, message: False,
            log_handler=lambda message, level=None, source=None: logs.append((message, level, source)),
        )

        self.assertTrue(result)
        self.assertTrue(any("已检测到 ffmpeg" in message for message, _, _ in logs))

    def test_startup_dependency_check_can_abort_when_ffmpeg_is_missing(self) -> None:
        prompts: list[tuple[str, str]] = []

        result = _ensure_runtime_dependencies(
            checker=_MissingChecker(),
            prompt_continue=lambda title, message: prompts.append((title, message)) or False,
        )

        self.assertFalse(result)
        self.assertEqual("缺少录制依赖", prompts[0][0])
        self.assertIn("暂时无法开始录制", prompts[0][1])

    def test_startup_dependency_check_can_continue_when_user_accepts_warning(self) -> None:
        result = _ensure_runtime_dependencies(
            checker=_MissingChecker(),
            prompt_continue=lambda title, message: True,
        )

        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
