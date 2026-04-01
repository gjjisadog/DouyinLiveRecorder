"""Desktop notification service."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from client.core.enums import TaskStatus
from client.core.models import AppConfig, RecordTask
from client.infra.logging.log_service import LEVEL_ERROR, LEVEL_INFO, LEVEL_WARNING, LogEmitterMixin, LogHandler, SOURCE_NOTIFICATION
from msg_push import bark, dingtalk, ntfy, pushplus, send_email, tg_bot, xizhi

NotificationSender = Callable[[str, str, str], None]

CHANNEL_WECHAT = "wechat"
CHANNEL_DINGTALK = "dingtalk"
CHANNEL_TELEGRAM = "telegram"
CHANNEL_BARK = "bark"
CHANNEL_NTFY = "ntfy"
CHANNEL_PUSHPLUS = "pushplus"
CHANNEL_EMAIL = "email"

CHANNEL_LABELS = {
    CHANNEL_WECHAT: "微信",
    CHANNEL_DINGTALK: "钉钉",
    CHANNEL_TELEGRAM: "Telegram",
    CHANNEL_BARK: "Bark",
    CHANNEL_NTFY: "ntfy",
    CHANNEL_PUSHPLUS: "PushPlus",
    CHANNEL_EMAIL: "邮件",
}

DESKTOP_CHANNEL_ALIASES = {
    "",
    "desktop",
    "local",
    "system",
    "tray",
    "桌面",
    "本地",
    "系统",
}
WECHAT_CHANNEL_ALIASES = {"微信", "wechat", "xizhi"}
DINGTALK_CHANNEL_ALIASES = {"钉钉", "dingtalk"}
TELEGRAM_CHANNEL_ALIASES = {"tg", "telegram", "电报"}
BARK_CHANNEL_ALIASES = {"bark"}
NTFY_CHANNEL_ALIASES = {"ntfy"}
PUSHPLUS_CHANNEL_ALIASES = {"pushplus", "push+"}
EMAIL_CHANNEL_ALIASES = {"email", "mail", "邮箱", "邮件"}
BOOL_TRUE = {"是", "true", "1", "yes", "on"}


@dataclass(slots=True)
class NotificationDispatchResult:
    channel: str
    success_count: int
    error_count: int
    message: str

    @property
    def ok(self) -> bool:
        return self.success_count > 0 and self.error_count == 0


class NotificationService(LogEmitterMixin):
    def __init__(
        self,
        config: AppConfig,
        log_handler: LogHandler | None = None,
        sender: NotificationSender | None = None,
    ) -> None:
        super().__init__(log_handler=log_handler, log_source=SOURCE_NOTIFICATION)
        self.config = config
        self._sender = sender

    def set_sender(self, sender: NotificationSender | None) -> None:
        self._sender = sender

    def notify(self, title: str, message: str, level: str = LEVEL_INFO) -> None:
        if not self.config.enable_notifications:
            return

        normalized_channels = self._normalized_channels()
        should_send_desktop = not normalized_channels or any(
            channel in DESKTOP_CHANNEL_ALIASES for channel in normalized_channels
        )
        remote_channels = [channel for channel in normalized_channels if channel not in DESKTOP_CHANNEL_ALIASES]

        if should_send_desktop and self._sender is not None:
            self._sender(title, message, level)
            self._emit_log(f"已发送桌面通知：{title}", LEVEL_INFO)
        elif should_send_desktop:
            self._emit_log(f"桌面通知未连接发送器，已跳过：{title}", LEVEL_WARNING)

        if remote_channels:
            self._notify_remote_channels(remote_channels, title, message)

    def notify_task_started(self, task: RecordTask) -> None:
        title = f"任务开始录制：{task.task_id}"
        message = f"{task.anchor_name or task.display_name or task.task_id} 已开始录制。"
        self.notify(title, message)

    def notify_task_finished(self, task: RecordTask, status: TaskStatus, error_message: str = "") -> None:
        if status == TaskStatus.COMPLETED:
            title = f"任务录制完成：{task.task_id}"
            message = f"{task.anchor_name or task.display_name or task.task_id} 已录制完成。"
        elif status == TaskStatus.FAILED:
            title = f"任务录制失败：{task.task_id}"
            message = error_message or task.last_error or "录制过程中发生未知错误。"
        elif status == TaskStatus.STOPPED:
            title = f"任务已停止：{task.task_id}"
            message = f"{task.anchor_name or task.display_name or task.task_id} 已停止录制。"
        else:
            title = f"任务状态更新：{task.task_id}"
            message = f"当前状态：{status.value}"
        self.notify(title, message, LEVEL_WARNING if status == TaskStatus.FAILED else LEVEL_INFO)

    def _normalized_channels(self) -> list[str]:
        raw_value = self.config.notify_channels.strip().replace("，", ",")
        if not raw_value:
            return []
        normalized_channels: list[str] = []
        for item in raw_value.split(","):
            normalized = self._normalize_channel(item)
            if normalized:
                normalized_channels.append(normalized)
        return normalized_channels

    def send_test_notification(self, channel: str) -> NotificationDispatchResult | None:
        normalized_channel = self._normalize_channel(channel)
        if normalized_channel is None:
            self._emit_log(f"未知的测试通知渠道：{channel}", LEVEL_WARNING)
            return None
        title = f"{CHANNEL_LABELS[normalized_channel]}测试通知"
        message = f"这是一条来自客户端的测试通知，发送时间：{datetime.now():%Y-%m-%d %H:%M:%S}"
        results = self._notify_remote_channels([normalized_channel], title, message)
        return results[0] if results else None

    def _notify_remote_channels(self, channels: list[str], title: str, message: str) -> list[NotificationDispatchResult]:
        results: list[NotificationDispatchResult] = []
        unsupported_channels: list[str] = []
        for channel in channels:
            if channel == CHANNEL_WECHAT:
                results.append(self._send_wechat(title, message))
                continue
            if channel == CHANNEL_DINGTALK:
                results.append(self._send_dingtalk(message))
                continue
            if channel == CHANNEL_TELEGRAM:
                results.append(self._send_telegram(message))
                continue
            if channel == CHANNEL_BARK:
                results.append(self._send_bark(title, message))
                continue
            if channel == CHANNEL_NTFY:
                results.append(self._send_ntfy(title, message))
                continue
            if channel == CHANNEL_PUSHPLUS:
                results.append(self._send_pushplus(title, message))
                continue
            if channel == CHANNEL_EMAIL:
                results.append(self._send_email(title, message))
                continue
            unsupported_channels.append(channel)

        if unsupported_channels:
            channels_text = "、".join(unsupported_channels)
            self._emit_log(f"以下通知渠道暂未接入，已跳过：{channels_text}", LEVEL_WARNING)
            for channel in unsupported_channels:
                results.append(
                    NotificationDispatchResult(
                        channel=channel,
                        success_count=0,
                        error_count=1,
                        message=f"{channel} 暂未接入",
                    )
                )
        return results

    def _send_wechat(self, title: str, message: str) -> NotificationDispatchResult:
        api_url = self._push_setting("微信推送接口链接")
        if not api_url:
            self._emit_log("未配置微信推送接口链接，已跳过微信通知。", LEVEL_WARNING)
            return NotificationDispatchResult(CHANNEL_WECHAT, 0, 1, "未配置微信推送接口链接")

        result = xizhi(api_url, title, message)
        return self._log_remote_result("微信", CHANNEL_WECHAT, result)

    def _send_dingtalk(self, message: str) -> NotificationDispatchResult:
        api_url = self._push_setting("钉钉推送接口链接")
        if not api_url:
            self._emit_log("未配置钉钉推送接口链接，已跳过钉钉通知。", LEVEL_WARNING)
            return NotificationDispatchResult(CHANNEL_DINGTALK, 0, 1, "未配置钉钉推送接口链接")

        phone_number = self._push_setting("钉钉通知@对象(填手机号)")
        is_atall = self._push_setting("钉钉通知@全体(是/否)").strip().lower() in BOOL_TRUE
        result = dingtalk(api_url, message, phone_number or None, is_atall)
        return self._log_remote_result("钉钉", CHANNEL_DINGTALK, result)

    def _send_telegram(self, message: str) -> NotificationDispatchResult:
        token = self._push_setting("tgapi令牌")
        chat_id = self._push_setting("tg聊天id(个人或者群组id)")
        if not token or not chat_id:
            self._emit_log("未配置 Telegram 令牌或聊天 ID，已跳过 Telegram 通知。", LEVEL_WARNING)
            return NotificationDispatchResult(CHANNEL_TELEGRAM, 0, 1, "未配置 Telegram 令牌或聊天 ID")

        result = tg_bot(chat_id, token, message)
        return self._log_remote_result("Telegram", CHANNEL_TELEGRAM, result)

    def _send_bark(self, title: str, message: str) -> NotificationDispatchResult:
        api_url = self._push_setting("Bark推送地址")
        if not api_url:
            self._emit_log("未配置 Bark 推送地址，已跳过 Bark 通知。", LEVEL_WARNING)
            return NotificationDispatchResult(CHANNEL_BARK, 0, 1, "未配置 Bark 推送地址")

        result = bark(api_url, title=title, content=message)
        return self._log_remote_result("Bark", CHANNEL_BARK, result)

    def _send_ntfy(self, title: str, message: str) -> NotificationDispatchResult:
        api_url = self._push_setting("ntfy推送地址")
        if not api_url:
            self._emit_log("未配置 ntfy 推送地址，已跳过 ntfy 通知。", LEVEL_WARNING)
            return NotificationDispatchResult(CHANNEL_NTFY, 0, 1, "未配置 ntfy 推送地址")

        tags = self._push_setting("ntfy标签") or "tada"
        result = ntfy(api_url, title=title, content=message, tags=tags)
        return self._log_remote_result("ntfy", CHANNEL_NTFY, result)

    def _send_pushplus(self, title: str, message: str) -> NotificationDispatchResult:
        token = self._push_setting("PushPlus令牌")
        if not token:
            self._emit_log("未配置 PushPlus 令牌，已跳过 PushPlus 通知。", LEVEL_WARNING)
            return NotificationDispatchResult(CHANNEL_PUSHPLUS, 0, 1, "未配置 PushPlus 令牌")

        result = pushplus(token, title, message)
        return self._log_remote_result("PushPlus", CHANNEL_PUSHPLUS, result)

    def _send_email(self, title: str, message: str) -> NotificationDispatchResult:
        email_host = self._push_setting("SMTP服务器")
        login_email = self._push_setting("邮箱账号")
        email_pass = self._push_setting("邮箱密码")
        sender_email = self._push_setting("发件邮箱")
        sender_name = self._push_setting("发件人名称")
        to_email = self._push_setting("收件邮箱")
        if not all((email_host, login_email, email_pass, sender_email, sender_name, to_email)):
            self._emit_log("未完整配置邮件通知参数，已跳过邮件通知。", LEVEL_WARNING)
            return NotificationDispatchResult(CHANNEL_EMAIL, 0, 1, "未完整配置邮件通知参数")

        smtp_port = self._push_setting("SMTP端口")
        open_ssl = self._push_setting("SMTP启用SSL(是/否)").strip().lower() in BOOL_TRUE
        result = send_email(
            email_host=email_host,
            login_email=login_email,
            email_pass=email_pass,
            sender_email=sender_email,
            sender_name=sender_name,
            to_email=to_email,
            title=title,
            content=message,
            smtp_port=smtp_port or None,
            open_ssl=open_ssl,
        )
        return self._log_remote_result("邮件", CHANNEL_EMAIL, result)

    def _log_remote_result(self, channel_name: str, channel: str, result: dict[str, Any]) -> NotificationDispatchResult:
        success = len(result.get("success", []))
        error = len(result.get("error", []))
        if success > 0 and error == 0:
            message = f"{channel_name} 通知发送成功，共 {success} 个目标。"
            self._emit_log(message, LEVEL_INFO)
            return NotificationDispatchResult(channel, success, error, message)
        if success > 0 and error > 0:
            message = f"{channel_name} 通知部分成功，成功 {success} 个，失败 {error} 个。"
            self._emit_log(message, LEVEL_WARNING)
            return NotificationDispatchResult(channel, success, error, message)
        message = f"{channel_name} 通知发送失败，失败 {error} 个目标。"
        self._emit_log(message, LEVEL_ERROR)
        return NotificationDispatchResult(channel, success, error, message)

    def _push_setting(self, key: str) -> str:
        return str(self.config.push_settings.get(key) or "").strip()

    def _normalize_channel(self, channel: str) -> str | None:
        normalized = channel.strip().lower()
        if not normalized:
            return None
        if normalized in WECHAT_CHANNEL_ALIASES:
            return CHANNEL_WECHAT
        if normalized in DINGTALK_CHANNEL_ALIASES:
            return CHANNEL_DINGTALK
        if normalized in TELEGRAM_CHANNEL_ALIASES:
            return CHANNEL_TELEGRAM
        if normalized in BARK_CHANNEL_ALIASES:
            return CHANNEL_BARK
        if normalized in NTFY_CHANNEL_ALIASES:
            return CHANNEL_NTFY
        if normalized in PUSHPLUS_CHANNEL_ALIASES:
            return CHANNEL_PUSHPLUS
        if normalized in EMAIL_CHANNEL_ALIASES:
            return CHANNEL_EMAIL
        if normalized in DESKTOP_CHANNEL_ALIASES:
            return normalized
        return None
