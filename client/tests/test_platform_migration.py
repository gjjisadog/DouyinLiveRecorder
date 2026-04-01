from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from client.core.enums import Platform
from client.core.models import AppConfig, RecordTask
from client.core.platform_router import PlatformRouter
from client.core.stream_resolver import StreamResolver


class PlatformMigrationTests(unittest.TestCase):
    def test_platform_router_detects_first_batch_migrated_platforms(self) -> None:
        router = PlatformRouter()

        cases = {
            "https://cc.163.com/583946984": Platform.NETEASE_CC,
            "https://qiandurebo.com/web/video.php?roomnumber=33333": Platform.QIANDUREBO,
            "https://www.pandalive.co.kr/live/play/bara0109": Platform.PANDATV,
            "https://live.baidu.com/m/media/pclive/pchome/live.html?room_id=9175031377&tab_category": Platform.BAIDU,
            "https://www.showroom-live.com/room/profile?room_id=480206": Platform.SHOWROOM,
            "https://chzzk.naver.com/live/458f6ec20b034f49e0fc6d03921646d2": Platform.CHZZK,
        }

        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(expected, router.detect_platform(url))

    def test_stream_resolver_resolves_netease_cc_via_legacy_modules(self) -> None:
        resolver = StreamResolver()
        config = AppConfig(quality="原画")
        task = RecordTask(task_id="task-101", url="https://cc.163.com/583946984", quality="超清")

        with (
            patch("src.spider.get_netease_stream_data", new=AsyncMock(return_value={"is_live": True, "title": "CC直播"})),
            patch(
                "src.stream.get_netease_stream_url",
                new=AsyncMock(
                    return_value={
                        "is_live": True,
                        "title": "CC直播",
                        "quality": "UHD",
                        "m3u8_url": "https://example.com/cc.m3u8",
                        "record_url": "https://example.com/cc.m3u8",
                    }
                ),
            ),
        ):
            stream_info = resolver.resolve_task(task, config)

        self.assertEqual(Platform.NETEASE_CC, task.platform)
        self.assertTrue(stream_info.is_live)
        self.assertEqual("https://example.com/cc.m3u8", stream_info.record_url)
        self.assertEqual("CC直播", stream_info.title)

    def test_stream_resolver_resolves_chzzk_with_generic_stream_helper(self) -> None:
        resolver = StreamResolver()
        config = AppConfig(quality="原画")
        task = RecordTask(
            task_id="task-102",
            url="https://chzzk.naver.com/live/458f6ec20b034f49e0fc6d03921646d2",
            quality="高清",
        )

        with (
            patch(
                "src.spider.get_chzzk_stream_data",
                new=AsyncMock(return_value={"is_live": True, "title": "CHZZK直播", "play_url_list": ["a", "b"]}),
            ),
            patch(
                "src.stream.get_stream_url",
                new=AsyncMock(
                    return_value={
                        "is_live": True,
                        "title": "CHZZK直播",
                        "quality": "HD",
                        "m3u8_url": "https://example.com/chzzk.m3u8",
                        "record_url": "https://example.com/chzzk.m3u8",
                    }
                ),
            ),
        ):
            stream_info = resolver.resolve_task(task, config)

        self.assertEqual(Platform.CHZZK, task.platform)
        self.assertTrue(stream_info.is_live)
        self.assertEqual("https://example.com/chzzk.m3u8", stream_info.m3u8_url)
        self.assertEqual("HD", stream_info.quality)


if __name__ == "__main__":
    unittest.main()
