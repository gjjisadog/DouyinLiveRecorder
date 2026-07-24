"""Platform routing."""

from urllib.parse import urlsplit

from client.core.enums import Platform
from client.core.exceptions import PlatformNotSupportedError
from client.platforms.base import PlatformAdapter

PLATFORM_RULES: list[tuple[Platform, tuple[str, ...]]] = [
    (Platform.DOUYIN, ("live.douyin.com", "v.douyin.com", "www.douyin.com")),
    (Platform.TIKTOK, ("www.tiktok.com",)),
    (Platform.KUAISHOU, ("live.kuaishou.com",)),
    (Platform.HUYA, ("www.huya.com",)),
    (Platform.DOUYU, ("www.douyu.com",)),
    (Platform.YY, ("www.yy.com",)),
    (Platform.BILIBILI, ("live.bilibili.com",)),
    (Platform.NETEASE_CC, ("cc.163.com",)),
    (Platform.QIANDUREBO, ("qiandurebo.com",)),
    (Platform.PANDATV, ("pandalive.co.kr",)),
    (Platform.BAIDU, ("live.baidu.com",)),
    (Platform.SHOWROOM, ("showroom-live.com",)),
    (Platform.CHZZK, ("chzzk.naver.com",)),
]


class PlatformRouter:
    def __init__(self, adapters: list[PlatformAdapter] | None = None) -> None:
        self.adapters = adapters or []

    def register(self, adapter: PlatformAdapter) -> None:
        self.adapters.append(adapter)

    def detect_platform(self, url: str) -> Platform:
        lower_url = url.lower()
        lower_path = urlsplit(lower_url).path
        if lower_path.endswith(".m3u8") or lower_path.endswith(".flv"):
            return Platform.DIRECT

        for platform, rules in PLATFORM_RULES:
            if any(rule in lower_url for rule in rules):
                return platform
        return Platform.UNKNOWN

    def resolve(self, url: str) -> PlatformAdapter:
        for adapter in self.adapters:
            if adapter.match(url):
                return adapter
        raise PlatformNotSupportedError(f"No platform adapter matched URL: {url}")
