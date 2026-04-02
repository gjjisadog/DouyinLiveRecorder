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

    def test_platform_router_detects_huya_douyu_yy_and_bilibili(self) -> None:
        router = PlatformRouter()

        cases = {
            "https://www.huya.com/880123": Platform.HUYA,
            "https://www.douyu.com/52222": Platform.DOUYU,
            "https://www.yy.com/22490906/22490906": Platform.YY,
            "https://live.bilibili.com/213": Platform.BILIBILI,
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

    def test_stream_resolver_resolves_huya_via_standard_branch(self) -> None:
        resolver = StreamResolver()
        config = AppConfig(quality="原画", cookies={"虎牙cookie": "huya-cookie"})
        task = RecordTask(task_id="task-201", url="https://www.huya.com/880123", quality="高清")

        with (
            patch(
                "src.spider.get_huya_stream_data",
                new=AsyncMock(return_value={"is_live": True, "title": "虎牙直播"}),
            ) as mock_room,
            patch(
                "src.stream.get_huya_stream_url",
                new=AsyncMock(
                    return_value={
                        "is_live": True,
                        "title": "虎牙直播",
                        "quality": "HD",
                        "flv_url": "https://example.com/huya.flv",
                        "record_url": "https://example.com/huya.flv",
                    }
                ),
            ) as mock_stream,
        ):
            stream_info = resolver.resolve_task(task, config)

        self.assertEqual(Platform.HUYA, task.platform)
        self.assertTrue(stream_info.is_live)
        self.assertEqual("https://example.com/huya.flv", stream_info.record_url)
        mock_room.assert_awaited_once_with(task.url, proxy_addr=None, cookies="huya-cookie")
        mock_stream.assert_awaited_once_with({"is_live": True, "title": "虎牙直播"}, "HD")

    def test_stream_resolver_resolves_douyu_via_legacy_modules(self) -> None:
        resolver = StreamResolver()
        config = AppConfig(quality="原画", cookies={"斗鱼cookie": "douyu-cookie"})
        task = RecordTask(task_id="task-202", url="https://www.douyu.com/52222", quality="超清")

        with (
            patch(
                "src.spider.get_douyu_info_data",
                new=AsyncMock(return_value={"room_id": "52222", "title": "斗鱼直播"}),
            ) as mock_room,
            patch(
                "src.stream.get_douyu_stream_url",
                new=AsyncMock(
                    return_value={
                        "is_live": True,
                        "title": "斗鱼直播",
                        "quality": "UHD",
                        "m3u8_url": "https://example.com/douyu.m3u8",
                        "record_url": "https://example.com/douyu.m3u8",
                    }
                ),
            ) as mock_stream,
        ):
            stream_info = resolver.resolve_task(task, config)

        self.assertEqual(Platform.DOUYU, task.platform)
        self.assertTrue(stream_info.is_live)
        self.assertEqual("https://example.com/douyu.m3u8", stream_info.record_url)
        mock_room.assert_awaited_once_with(task.url, proxy_addr=None, cookies="douyu-cookie")
        mock_stream.assert_awaited_once_with(
            {"room_id": "52222", "title": "斗鱼直播"},
            video_quality="UHD",
            cookies="douyu-cookie",
            proxy_addr=None,
        )

    def test_stream_resolver_resolves_yy_via_legacy_modules(self) -> None:
        resolver = StreamResolver()
        config = AppConfig(quality="原画", cookies={"yy_cookie": "yy-cookie"})
        task = RecordTask(task_id="task-203", url="https://www.yy.com/22490906/22490906")

        with (
            patch(
                "src.spider.get_yy_stream_data",
                new=AsyncMock(return_value={"room_id": "22490906", "title": "YY直播"}),
            ) as mock_room,
            patch(
                "src.stream.get_yy_stream_url",
                new=AsyncMock(
                    return_value={
                        "is_live": True,
                        "title": "YY直播",
                        "quality": "OD",
                        "flv_url": "https://example.com/yy.flv",
                        "record_url": "https://example.com/yy.flv",
                    }
                ),
            ) as mock_stream,
        ):
            stream_info = resolver.resolve_task(task, config)

        self.assertEqual(Platform.YY, task.platform)
        self.assertTrue(stream_info.is_live)
        self.assertEqual("https://example.com/yy.flv", stream_info.record_url)
        mock_room.assert_awaited_once_with(task.url, proxy_addr=None, cookies="yy-cookie")
        mock_stream.assert_awaited_once_with({"room_id": "22490906", "title": "YY直播"})

    def test_stream_resolver_resolves_bilibili_via_legacy_modules(self) -> None:
        resolver = StreamResolver()
        config = AppConfig(quality="原画", cookies={"b站cookie": "bilibili-cookie"})
        task = RecordTask(task_id="task-204", url="https://live.bilibili.com/213", quality="超清")

        with (
            patch(
                "src.spider.get_bilibili_room_info",
                new=AsyncMock(return_value={"room_id": "213", "title": "B站直播"}),
            ) as mock_room,
            patch(
                "src.stream.get_bilibili_stream_url",
                new=AsyncMock(
                    return_value={
                        "is_live": True,
                        "title": "B站直播",
                        "quality": "UHD",
                        "m3u8_url": "https://example.com/bilibili.m3u8",
                        "record_url": "https://example.com/bilibili.m3u8",
                    }
                ),
            ) as mock_stream,
        ):
            stream_info = resolver.resolve_task(task, config)

        self.assertEqual(Platform.BILIBILI, task.platform)
        self.assertTrue(stream_info.is_live)
        self.assertEqual("https://example.com/bilibili.m3u8", stream_info.record_url)
        mock_room.assert_awaited_once_with(task.url, proxy_addr=None, cookies="bilibili-cookie")
        mock_stream.assert_awaited_once_with(
            {"room_id": "213", "title": "B站直播"},
            video_quality="UHD",
            proxy_addr=None,
            cookies="bilibili-cookie",
        )


if __name__ == "__main__":
    unittest.main()
