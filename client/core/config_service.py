"""Legacy configuration loading for the desktop client."""

from __future__ import annotations

import configparser
import re
from pathlib import Path

from client.core.enums import OutputFormat
from client.core.models import AppConfig, RecordTask
from client.core.platform_router import PlatformRouter
from client.infra.logging.log_service import LEVEL_DEBUG, LEVEL_INFO, LEVEL_WARNING, LogEmitterMixin, LogHandler, SOURCE_CONFIG
from client.infra.storage.json_store import JsonStore

TEXT_ENCODING = "utf-8-sig"
RECORD_SECTION = "\u5f55\u5236\u8bbe\u7f6e"
PUSH_SECTION = "\u63a8\u9001\u914d\u7f6e"
COOKIE_SECTION = "Cookie"
AUTH_SECTION = "Authorization"
CREDENTIAL_SECTION = "\u8d26\u53f7\u5bc6\u7801"
QUALITY_NAMES = {
    "\u539f\u753b",
    "\u84dd\u5149",
    "\u8d85\u6e05",
    "\u9ad8\u6e05",
    "\u6807\u6e05",
    "\u6d41\u7545",
}
BOOL_TRUE = {"\u662f", "true", "1", "yes", "on"}


class ConfigService(LogEmitterMixin):
    def __init__(
        self,
        root_dir: Path | None = None,
        local_config_path: Path | None = None,
        log_handler: LogHandler | None = None,
    ) -> None:
        super().__init__(log_handler=log_handler, log_source=SOURCE_CONFIG)
        self.root_dir = root_dir or Path(__file__).resolve().parents[2]
        self.config_path = self.root_dir / "config" / "config.ini"
        self.url_config_path = self.root_dir / "config" / "URL_config.ini"
        self.local_config_path = local_config_path
        self.local_store = JsonStore(local_config_path) if local_config_path is not None else None
        self.platform_router = PlatformRouter()

    def load(self) -> AppConfig:
        self._emit_log("开始加载客户端配置。", LEVEL_DEBUG)
        local_config = self.load_local()
        if local_config is not None:
            self._emit_log("已从本地配置文件加载客户端配置。", LEVEL_INFO)
            return local_config

        self._emit_log("未找到本地配置，将回退到旧版配置文件。", LEVEL_WARNING)
        config, _ = self.load_legacy()
        self.save(config)
        self._emit_log("已完成旧版配置迁移，并写入本地配置文件。", LEVEL_INFO)
        return config

    def load_legacy(self) -> tuple[AppConfig, list[RecordTask]]:
        self._emit_log(f"开始读取旧版配置文件：{self.config_path}", LEVEL_DEBUG)
        parser = configparser.RawConfigParser()
        parser.read(self.config_path, encoding=TEXT_ENCODING)

        output_dir_raw = self._get(
            parser,
            RECORD_SECTION,
            "\u76f4\u64ad\u4fdd\u5b58\u8def\u5f84(\u4e0d\u586b\u5219\u9ed8\u8ba4)",
            "",
        ).strip()
        output_dir = Path(output_dir_raw) if output_dir_raw else self.root_dir / "downloads"

        config = AppConfig(
            output_dir=output_dir,
            output_format=self._parse_output_format(
                self._get(
                    parser,
                    RECORD_SECTION,
                    "\u89c6\u9891\u4fdd\u5b58\u683c\u5f0fts|mkv|flv|mp4|mp3\u97f3\u9891|m4a\u97f3\u9891",
                    "ts",
                )
            ),
            quality=self._get(
                parser,
                RECORD_SECTION,
                "\u539f\u753b|\u8d85\u6e05|\u9ad8\u6e05|\u6807\u6e05|\u6d41\u7545",
                "\u539f\u753b",
            ),
            max_file_size_gb=1.0,
            max_concurrency=int(
                self._get(
                    parser,
                    RECORD_SECTION,
                    "\u540c\u4e00\u65f6\u95f4\u8bbf\u95ee\u7f51\u7edc\u7684\u7ebf\u7a0b\u6570",
                    3,
                )
            ),
            loop_seconds=int(self._get(parser, RECORD_SECTION, "\u5faa\u73af\u65f6\u95f4(\u79d2)", 300)),
            queue_seconds=int(
                self._get(parser, RECORD_SECTION, "\u6392\u961f\u8bfb\u53d6\u7f51\u5740\u65f6\u95f4(\u79d2)", 0)
            ),
            split_recording=self._get_bool(
                parser,
                RECORD_SECTION,
                "\u5206\u6bb5\u5f55\u5236\u662f\u5426\u5f00\u542f",
                True,
            ),
            split_seconds=int(self._get(parser, RECORD_SECTION, "\u89c6\u9891\u5206\u6bb5\u65f6\u95f4(\u79d2)", 1800)),
            use_proxy=self._get_bool(
                parser,
                RECORD_SECTION,
                "\u662f\u5426\u4f7f\u7528\u4ee3\u7406ip(\u662f/\u5426)",
                False,
            ),
            proxy_url=self._get(parser, RECORD_SECTION, "\u4ee3\u7406\u5730\u5740", ""),
            use_https_recording=self._get_bool(
                parser,
                RECORD_SECTION,
                "\u662f\u5426\u5f3a\u5236\u542f\u7528https\u5f55\u5236",
                False,
            ),
            folder_by_author=self._get_bool(
                parser,
                RECORD_SECTION,
                "\u4fdd\u5b58\u6587\u4ef6\u5939\u662f\u5426\u4ee5\u4f5c\u8005\u533a\u5206",
                True,
            ),
            folder_by_time=self._get_bool(
                parser,
                RECORD_SECTION,
                "\u4fdd\u5b58\u6587\u4ef6\u5939\u662f\u5426\u4ee5\u65f6\u95f4\u533a\u5206",
                False,
            ),
            folder_by_title=self._get_bool(
                parser,
                RECORD_SECTION,
                "\u4fdd\u5b58\u6587\u4ef6\u5939\u662f\u5426\u4ee5\u6807\u9898\u533a\u5206",
                False,
            ),
            filename_include_title=self._get_bool(
                parser,
                RECORD_SECTION,
                "\u4fdd\u5b58\u6587\u4ef6\u540d\u662f\u5426\u5305\u542b\u6807\u9898",
                False,
            ),
            clean_emoji=self._get_bool(
                parser,
                RECORD_SECTION,
                "\u662f\u5426\u53bb\u9664\u540d\u79f0\u4e2d\u7684\u8868\u60c5\u7b26\u53f7",
                True,
            ),
            disk_space_limit_gb=float(
                self._get(parser, RECORD_SECTION, "\u5f55\u5236\u7a7a\u95f4\u5269\u4f59\u9608\u503c(gb)", 1.0)
            ),
            convert_to_mp4=self._get_bool(
                parser,
                RECORD_SECTION,
                "\u5f55\u5236\u5b8c\u6210\u540e\u81ea\u52a8\u8f6c\u4e3amp4\u683c\u5f0f",
                False,
            ),
            convert_to_h264=self._get_bool(
                parser,
                RECORD_SECTION,
                "mp4\u683c\u5f0f\u91cd\u65b0\u7f16\u7801\u4e3ah264",
                False,
            ),
            delete_origin_after_convert=self._get_bool(
                parser,
                RECORD_SECTION,
                "\u8ffd\u52a0\u683c\u5f0f\u540e\u5220\u9664\u539f\u6587\u4ef6",
                True,
            ),
            create_time_file=self._get_bool(
                parser,
                RECORD_SECTION,
                "\u751f\u6210\u65f6\u95f4\u5b57\u5e55\u6587\u4ef6",
                False,
            ),
            show_source_url=self._get_bool(
                parser,
                RECORD_SECTION,
                "\u662f\u5426\u663e\u793a\u76f4\u64ad\u6e90\u5730\u5740",
                False,
            ),
            disable_record=self._get_bool(
                parser,
                PUSH_SECTION,
                "\u53ea\u63a8\u9001\u901a\u77e5\u4e0d\u5f55\u5236(\u662f/\u5426)",
                False,
            ),
            custom_script=self._get(
                parser,
                RECORD_SECTION,
                "\u81ea\u5b9a\u4e49\u811a\u672c\u6267\u884c\u547d\u4ee4",
                "",
            ),
            enable_notifications=bool(
                self._get(parser, PUSH_SECTION, "\u76f4\u64ad\u72b6\u6001\u63a8\u9001\u6e20\u9053", "").strip()
            ),
            notify_channels=self._get(parser, PUSH_SECTION, "\u76f4\u64ad\u72b6\u6001\u63a8\u9001\u6e20\u9053", ""),
            douyin_cookie=self._get(parser, COOKIE_SECTION, "\u6296\u97f3cookie", ""),
            push_settings=self._read_section(parser, PUSH_SECTION),
            cookies=self._read_section(parser, COOKIE_SECTION),
            authorization=self._read_section(parser, AUTH_SECTION),
            credentials=self._read_section(parser, CREDENTIAL_SECTION),
            proxy_platforms=self._split_csv(
                self._get(
                    parser,
                    RECORD_SECTION,
                    "\u4f7f\u7528\u4ee3\u7406\u5f55\u5236\u7684\u5e73\u53f0(\u9017\u53f7\u5206\u9694)",
                    "",
                )
            ),
            extra_proxy_platforms=self._split_csv(
                self._get(
                    parser,
                    RECORD_SECTION,
                    "\u989d\u5916\u4f7f\u7528\u4ee3\u7406\u5f55\u5236\u7684\u5e73\u53f0(\u9017\u53f7\u5206\u9694)",
                    "",
                )
            ),
            minimize_to_tray=True,
            close_to_tray=True,
            start_on_boot=False,
            restore_tasks_on_launch=True,
            restore_window_on_launch=True,
            legacy_config_path=self.config_path,
            legacy_url_config_path=self.url_config_path,
        )
        tasks = self.load_tasks(self.url_config_path, config.quality)
        self._emit_log(f"已从旧版配置加载 {len(tasks)} 个任务。", LEVEL_INFO)
        return config, tasks

    def save(self, config: AppConfig) -> None:
        if self.local_store is None:
            self._emit_log("当前未配置本地配置文件路径，已跳过保存。", LEVEL_WARNING)
            return
        payload = {
            "version": 1,
            "config": self._serialize_config(config),
        }
        self.local_store.save(payload)
        self._emit_log(f"本地配置已保存：{self.local_config_path}", LEVEL_INFO)

    def import_legacy_ini(self, file_path: str) -> AppConfig:
        _ = file_path
        self._emit_log("开始导入旧版 INI 配置。", LEVEL_INFO)
        config, _ = self.load_legacy()
        return config

    def load_local(self) -> AppConfig | None:
        if self.local_store is None:
            self._emit_log("当前未启用本地配置存储。", LEVEL_DEBUG)
            return None

        payload = self.local_store.load(on_error=self._handle_local_store_error)
        if not isinstance(payload, dict):
            self._emit_log("本地配置文件不存在或内容为空。", LEVEL_DEBUG)
            return None

        config_payload = payload.get("config", payload)
        if not isinstance(config_payload, dict):
            self._emit_log("本地配置文件结构无效，将忽略并回退。", LEVEL_WARNING)
            return None
        self._emit_log(f"已读取本地配置文件：{self.local_config_path}", LEVEL_DEBUG)
        return self._deserialize_config(config_payload)

    def _handle_local_store_error(self, exc: Exception, path: Path, backup_path: Path | None) -> None:
        suffix = f"，已备份到 {backup_path}" if backup_path is not None else ""
        self._emit_log(f"读取本地配置失败：{path}，将回退到旧版配置。{exc}{suffix}", LEVEL_WARNING)

    def load_tasks(self, url_config_path: Path | None = None, default_quality: str = "\u539f\u753b") -> list[RecordTask]:
        path = url_config_path or self.url_config_path
        if not path.exists():
            self._emit_log(f"旧版任务配置文件不存在：{path}", LEVEL_WARNING)
            return []

        tasks: list[RecordTask] = []
        for line_number, raw_line in enumerate(path.read_text(encoding=TEXT_ENCODING, errors="ignore").splitlines(), start=1):
            original = raw_line.strip()
            if not original:
                continue

            enabled = not original.startswith("#")
            line = original.lstrip("#").strip()
            if len(line) < 5:
                continue

            parts = [part.strip() for part in re.split(r"[,，]", line) if part.strip()]
            quality = default_quality
            url = ""
            display_name = ""

            if len(parts) == 1:
                url = parts[0]
            elif len(parts) == 2:
                if self._contains_url(parts[0]):
                    url, display_name = parts
                else:
                    quality, url = parts
            else:
                quality, url, display_name = parts[0], parts[1], parts[2]

            if quality not in QUALITY_NAMES:
                quality = default_quality
            if "://" not in url:
                url = f"https://{url}"

            tasks.append(
                RecordTask(
                    task_id=f"task-{line_number:03d}",
                    url=url,
                    platform=self.platform_router.detect_platform(url),
                    quality=quality,
                    enabled=enabled,
                    display_name=display_name,
                )
            )
        self._emit_log(f"已从 {path.name} 解析到 {len(tasks)} 个旧版任务。", LEVEL_DEBUG)
        return tasks

    def _get(self, parser: configparser.RawConfigParser, section: str, option: str, default: str | int | float) -> str:
        if not parser.has_section(section):
            return str(default)
        return parser.get(section, option, fallback=str(default))

    def _get_bool(self, parser: configparser.RawConfigParser, section: str, option: str, default: bool) -> bool:
        value = self._get(parser, section, option, "\u662f" if default else "\u5426")
        return str(value).strip().lower() in BOOL_TRUE

    def _parse_output_format(self, raw_value: str) -> OutputFormat:
        normalized = raw_value.strip().lower()
        if "m4a" in normalized:
            return OutputFormat.M4A
        if "mp3" in normalized:
            return OutputFormat.MP3
        for fmt in OutputFormat:
            if normalized == fmt.value:
                return fmt
        return OutputFormat.TS

    def _read_section(self, parser: configparser.RawConfigParser, section: str) -> dict[str, str]:
        if not parser.has_section(section):
            return {}
        return {key: value for key, value in parser.items(section)}

    def _split_csv(self, raw_value: str) -> list[str]:
        return [item.strip().lower() for item in raw_value.split(",") if item.strip()]

    def _contains_url(self, value: str) -> bool:
        pattern = r"(https?://)?(www\.)?[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+(:\d+)?(/.*)?"
        return re.search(pattern, value) is not None

    def _serialize_config(self, config: AppConfig) -> dict:
        return {
            "output_dir": str(config.output_dir),
            "output_format": config.output_format.value,
            "quality": config.quality,
            "max_file_size_gb": config.max_file_size_gb,
            "max_concurrency": config.max_concurrency,
            "loop_seconds": config.loop_seconds,
            "queue_seconds": config.queue_seconds,
            "split_recording": config.split_recording,
            "split_seconds": config.split_seconds,
            "use_proxy": config.use_proxy,
            "proxy_url": config.proxy_url,
            "use_https_recording": config.use_https_recording,
            "folder_by_author": config.folder_by_author,
            "folder_by_time": config.folder_by_time,
            "folder_by_title": config.folder_by_title,
            "filename_include_title": config.filename_include_title,
            "clean_emoji": config.clean_emoji,
            "disk_space_limit_gb": config.disk_space_limit_gb,
            "convert_to_mp4": config.convert_to_mp4,
            "convert_to_h264": config.convert_to_h264,
            "delete_origin_after_convert": config.delete_origin_after_convert,
            "create_time_file": config.create_time_file,
            "show_source_url": config.show_source_url,
            "disable_record": config.disable_record,
            "custom_script": config.custom_script,
            "enable_notifications": config.enable_notifications,
            "notify_channels": config.notify_channels,
            "douyin_cookie": config.douyin_cookie,
            "push_settings": config.push_settings,
            "cookies": config.cookies,
            "authorization": config.authorization,
            "credentials": config.credentials,
            "proxy_platforms": config.proxy_platforms,
            "extra_proxy_platforms": config.extra_proxy_platforms,
            "minimize_to_tray": config.minimize_to_tray,
            "close_to_tray": config.close_to_tray,
            "start_on_boot": config.start_on_boot,
            "restore_tasks_on_launch": config.restore_tasks_on_launch,
            "restore_window_on_launch": config.restore_window_on_launch,
        }

    def _deserialize_config(self, payload: dict) -> AppConfig:
        output_format = self._parse_output_format(str(payload.get("output_format", "ts")))
        output_dir = Path(str(payload.get("output_dir") or self.root_dir / "downloads"))
        return AppConfig(
            output_dir=output_dir,
            output_format=output_format,
            quality=str(payload.get("quality") or "\u539f\u753b"),
            max_file_size_gb=float(payload.get("max_file_size_gb", 1.0)),
            max_concurrency=int(payload.get("max_concurrency", 3)),
            loop_seconds=int(payload.get("loop_seconds", 300)),
            queue_seconds=int(payload.get("queue_seconds", 0)),
            split_recording=bool(payload.get("split_recording", True)),
            split_seconds=int(payload.get("split_seconds", 1800)),
            use_proxy=bool(payload.get("use_proxy", False)),
            proxy_url=str(payload.get("proxy_url") or ""),
            use_https_recording=bool(payload.get("use_https_recording", False)),
            folder_by_author=bool(payload.get("folder_by_author", True)),
            folder_by_time=bool(payload.get("folder_by_time", False)),
            folder_by_title=bool(payload.get("folder_by_title", False)),
            filename_include_title=bool(payload.get("filename_include_title", False)),
            clean_emoji=bool(payload.get("clean_emoji", True)),
            disk_space_limit_gb=float(payload.get("disk_space_limit_gb", 1.0)),
            convert_to_mp4=bool(payload.get("convert_to_mp4", True)),
            convert_to_h264=bool(payload.get("convert_to_h264", False)),
            delete_origin_after_convert=bool(payload.get("delete_origin_after_convert", True)),
            create_time_file=bool(payload.get("create_time_file", False)),
            show_source_url=bool(payload.get("show_source_url", False)),
            disable_record=bool(payload.get("disable_record", False)),
            custom_script=str(payload.get("custom_script") or ""),
            enable_notifications=bool(payload.get("enable_notifications", False)),
            notify_channels=str(payload.get("notify_channels") or ""),
            douyin_cookie=str(payload.get("douyin_cookie") or ""),
            push_settings=dict(payload.get("push_settings") or {}),
            cookies=dict(payload.get("cookies") or {}),
            authorization=dict(payload.get("authorization") or {}),
            credentials=dict(payload.get("credentials") or {}),
            proxy_platforms=list(payload.get("proxy_platforms") or []),
            extra_proxy_platforms=list(payload.get("extra_proxy_platforms") or []),
            minimize_to_tray=bool(payload.get("minimize_to_tray", True)),
            close_to_tray=bool(payload.get("close_to_tray", True)),
            start_on_boot=bool(payload.get("start_on_boot", False)),
            restore_tasks_on_launch=bool(payload.get("restore_tasks_on_launch", True)),
            restore_window_on_launch=bool(payload.get("restore_window_on_launch", True)),
            legacy_config_path=self.config_path,
            legacy_url_config_path=self.url_config_path,
        )
