"""Dependency checks for client runtime."""

from shutil import which

from client.core.exceptions import DependencyMissingError


class DependencyChecker:
    def find_ffmpeg(self) -> str | None:
        return which("ffmpeg")

    def ensure_ffmpeg(self) -> str:
        ffmpeg_path = self.find_ffmpeg()
        if ffmpeg_path is None:
            raise DependencyMissingError("未检测到 ffmpeg，请先安装并确保其已加入 PATH。")
        return ffmpeg_path
