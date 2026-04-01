"""Stream resolution using the legacy crawler modules."""

from __future__ import annotations

import asyncio

from client.core.enums import Platform
from client.core.exceptions import PlatformNotSupportedError
from client.core.models import AppConfig, RecordTask, StreamInfo
from client.core.platform_router import PlatformRouter
from client.infra.logging.log_service import LEVEL_DEBUG, LEVEL_ERROR, LEVEL_INFO, LogEmitterMixin, SOURCE_RECORD
from client.platforms.base import PlatformAdapter

QUALITY_CODE_MAP = {
    "\u539f\u753b": "OD",
    "\u84dd\u5149": "BD",
    "\u8d85\u6e05": "UHD",
    "\u9ad8\u6e05": "HD",
    "\u6807\u6e05": "SD",
    "\u6d41\u7545": "LD",
}


class StreamResolver(LogEmitterMixin):
    def __init__(self, platform_router: PlatformRouter | None = None) -> None:
        super().__init__(log_source=SOURCE_RECORD)
        self.platform_router = platform_router or PlatformRouter()

    def resolve(self, adapter: PlatformAdapter, task: RecordTask, config: AppConfig) -> StreamInfo:
        room_data = adapter.fetch_room(task.url, config)
        return adapter.resolve_stream(room_data, config.quality, config)

    def resolve_task(self, task: RecordTask, config: AppConfig) -> StreamInfo:
        from src import spider, stream

        task.platform = task.platform if task.platform != Platform.UNKNOWN else self.platform_router.detect_platform(task.url)
        quality_code = self.get_quality_code(task.quality or config.quality)
        proxy_address = self._select_proxy(task.url, config)
        self._emit_log(
            f"开始解析任务 {task.task_id}，平台 {task.platform.value}，画质 {task.quality or config.quality}。",
            LEVEL_DEBUG,
        )
        if proxy_address:
            self._emit_log(f"任务 {task.task_id} 解析直播流时将使用代理。", LEVEL_DEBUG)

        if task.platform == Platform.DIRECT:
            stream_info = StreamInfo(
                is_live=True,
                title=task.title or task.display_name or task.task_id,
                quality=quality_code,
                record_url=task.url,
                m3u8_url=task.url if task.url.endswith(".m3u8") else "",
                flv_url=task.url if task.url.endswith(".flv") else "",
            )
            self._log_resolved(task, stream_info)
            return stream_info

        if task.platform == Platform.DOUYIN:
            cookie = self._cookie(config, "\u6296\u97f3cookie", "douyincookie")
            if "v.douyin.com" not in task.url and "/user/" not in task.url:
                room_data = asyncio.run(
                    spider.get_douyin_web_stream_data(task.url, proxy_addr=proxy_address, cookies=cookie)
                )
            else:
                room_data = asyncio.run(
                    spider.get_douyin_app_stream_data(task.url, proxy_addr=proxy_address, cookies=cookie)
                )
            stream_info = self._to_stream_info(
                asyncio.run(stream.get_douyin_stream_url(room_data, quality_code, proxy_address))
            )
            self._log_resolved(task, stream_info)
            return stream_info

        if task.platform == Platform.TIKTOK:
            room_data = asyncio.run(
                spider.get_tiktok_stream_data(
                    task.url,
                    proxy_addr=proxy_address,
                    cookies=self._cookie(config, "tiktok_cookie"),
                )
            )
            stream_info = self._to_stream_info(
                asyncio.run(stream.get_tiktok_stream_url(room_data, quality_code, proxy_address))
            )
            self._log_resolved(task, stream_info)
            return stream_info

        if task.platform == Platform.KUAISHOU:
            room_data = asyncio.run(
                spider.get_kuaishou_stream_data(
                    task.url,
                    proxy_addr=proxy_address,
                    cookies=self._cookie(config, "\u5feb\u624bcookie", "kuaishoucookie"),
                )
            )
            stream_info = self._to_stream_info(asyncio.run(stream.get_kuaishou_stream_url(room_data, quality_code)))
            self._log_resolved(task, stream_info)
            return stream_info

        if task.platform == Platform.HUYA:
            cookie = self._cookie(config, "\u864e\u7259cookie", "huyacookie")
            if quality_code not in {"OD", "BD", "UHD"}:
                room_data = asyncio.run(spider.get_huya_stream_data(task.url, proxy_addr=proxy_address, cookies=cookie))
                stream_info = self._to_stream_info(asyncio.run(stream.get_huya_stream_url(room_data, quality_code)))
                self._log_resolved(task, stream_info)
                return stream_info
            stream_info = self._to_stream_info(
                asyncio.run(spider.get_huya_app_stream_url(task.url, proxy_addr=proxy_address, cookies=cookie))
            )
            self._log_resolved(task, stream_info)
            return stream_info

        if task.platform == Platform.DOUYU:
            cookie = self._cookie(config, "\u6597\u9c7ccookie", "douyucookie")
            room_data = asyncio.run(spider.get_douyu_info_data(task.url, proxy_addr=proxy_address, cookies=cookie))
            stream_info = self._to_stream_info(
                asyncio.run(
                    stream.get_douyu_stream_url(
                        room_data,
                        video_quality=quality_code,
                        cookies=cookie,
                        proxy_addr=proxy_address,
                    )
                )
            )
            self._log_resolved(task, stream_info)
            return stream_info

        if task.platform == Platform.YY:
            room_data = asyncio.run(
                spider.get_yy_stream_data(
                    task.url,
                    proxy_addr=proxy_address,
                    cookies=self._cookie(config, "yy_cookie"),
                )
            )
            stream_info = self._to_stream_info(asyncio.run(stream.get_yy_stream_url(room_data)))
            self._log_resolved(task, stream_info)
            return stream_info

        if task.platform == Platform.BILIBILI:
            cookie = self._cookie(config, "b\u7ad9cookie", "bilibilicookie")
            room_data = asyncio.run(
                spider.get_bilibili_room_info(task.url, proxy_addr=proxy_address, cookies=cookie)
            )
            stream_info = self._to_stream_info(
                asyncio.run(
                    stream.get_bilibili_stream_url(
                        room_data,
                        video_quality=quality_code,
                        proxy_addr=proxy_address,
                        cookies=cookie,
                    )
                )
            )
            self._log_resolved(task, stream_info)
            return stream_info

        if task.platform == Platform.NETEASE_CC:
            room_data = asyncio.run(
                spider.get_netease_stream_data(
                    task.url,
                    proxy_addr=proxy_address,
                    cookies=self._cookie(config, "网易cccookie", "netease_cookie", "cc_cookie"),
                )
            )
            stream_info = self._to_stream_info(asyncio.run(stream.get_netease_stream_url(room_data, quality_code)))
            self._log_resolved(task, stream_info)
            return stream_info

        if task.platform == Platform.QIANDUREBO:
            room_data = asyncio.run(
                spider.get_qiandurebo_stream_data(
                    task.url,
                    proxy_addr=proxy_address,
                    cookies=self._cookie(config, "qiandurebocookie"),
                )
            )
            stream_info = self._to_stream_info(room_data)
            self._log_resolved(task, stream_info)
            return stream_info

        if task.platform == Platform.PANDATV:
            room_data = asyncio.run(
                spider.get_pandatv_stream_data(
                    task.url,
                    proxy_addr=proxy_address,
                    cookies=self._cookie(config, "pandalivecookie", "pandatvcookie"),
                )
            )
            stream_info = self._to_stream_info(asyncio.run(stream.get_stream_url(room_data, quality_code)))
            self._log_resolved(task, stream_info)
            return stream_info

        if task.platform == Platform.BAIDU:
            room_data = asyncio.run(
                spider.get_baidu_stream_data(
                    task.url,
                    proxy_addr=proxy_address,
                    cookies=self._cookie(config, "baiducookie"),
                )
            )
            stream_info = self._to_stream_info(asyncio.run(stream.get_stream_url(room_data, quality_code)))
            self._log_resolved(task, stream_info)
            return stream_info

        if task.platform == Platform.SHOWROOM:
            room_data = asyncio.run(
                spider.get_showroom_stream_data(
                    task.url,
                    proxy_addr=proxy_address,
                    cookies=self._cookie(config, "showroomcookie"),
                )
            )
            stream_info = self._to_stream_info(asyncio.run(stream.get_stream_url(room_data, quality_code)))
            self._log_resolved(task, stream_info)
            return stream_info

        if task.platform == Platform.CHZZK:
            room_data = asyncio.run(
                spider.get_chzzk_stream_data(
                    task.url,
                    proxy_addr=proxy_address,
                    cookies=self._cookie(config, "chzzkcookie"),
                )
            )
            stream_info = self._to_stream_info(asyncio.run(stream.get_stream_url(room_data, quality_code)))
            self._log_resolved(task, stream_info)
            return stream_info

        self._emit_log(f"任务 {task.task_id} 仍未支持该平台：{task.url}", LEVEL_ERROR)
        raise PlatformNotSupportedError(f"Platform is not yet migrated into client/core: {task.url}")

    def get_quality_code(self, quality_name: str) -> str:
        return QUALITY_CODE_MAP.get(quality_name, "OD")

    def _to_stream_info(self, data: dict) -> StreamInfo:
        return StreamInfo(
            is_live=data.get("is_live", False),
            title=data.get("title", ""),
            quality=data.get("quality", ""),
            m3u8_url=data.get("m3u8_url", ""),
            flv_url=data.get("flv_url", ""),
            record_url=data.get("record_url", ""),
            headers=data.get("headers", {}),
        )

    def _select_proxy(self, url: str, config: AppConfig) -> str | None:
        if not config.use_proxy or not config.proxy_url:
            return None

        lower_url = url.lower()
        if not config.proxy_platforms and not config.extra_proxy_platforms:
            return config.proxy_url
        if any(platform in lower_url for platform in config.proxy_platforms):
            return config.proxy_url
        if any(platform in lower_url for platform in config.extra_proxy_platforms):
            return config.proxy_url
        return None

    def _cookie(self, config: AppConfig, *candidate_names: str) -> str:
        for name in candidate_names:
            for key, value in config.cookies.items():
                if key.lower() == name.lower():
                    return value
        return ""

    def _log_resolved(self, task: RecordTask, stream_info: StreamInfo) -> None:
        if stream_info.is_live:
            self._emit_log(
                f"任务 {task.task_id} 已解析到直播流，标题：{stream_info.title or task.title or '未命名直播'}。",
                LEVEL_INFO,
            )
            return
        self._emit_log(f"任务 {task.task_id} 当前未开播。", LEVEL_INFO)
