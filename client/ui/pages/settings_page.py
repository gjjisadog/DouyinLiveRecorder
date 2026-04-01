"""Settings page UI."""

from __future__ import annotations

from pathlib import Path
import re

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from client.core.config_service import ConfigService
from client.core.enums import OutputFormat
from client.core.models import AppConfig
from client.core.notification_service import (
    CHANNEL_BARK,
    CHANNEL_DINGTALK,
    CHANNEL_EMAIL,
    CHANNEL_NTFY,
    CHANNEL_PUSHPLUS,
    CHANNEL_TELEGRAM,
    CHANNEL_WECHAT,
    NotificationService,
)
from client.infra.logging.log_service import LEVEL_DEBUG, LEVEL_ERROR, LEVEL_INFO, LEVEL_WARNING, SOURCE_NOTIFICATION, SOURCE_SETTINGS
from client.infra.process.desktop_runtime import DesktopRuntimeService
from client.viewmodels.settings_viewmodel import SettingsViewModel

QUALITY_OPTIONS = ["原画", "蓝光", "超清", "高清", "标清", "流畅"]
PUSH_WECHAT_URL = "微信推送接口链接"
PUSH_DINGTALK_URL = "钉钉推送接口链接"
PUSH_DINGTALK_PHONE = "钉钉通知@对象(填手机号)"
PUSH_DINGTALK_AT_ALL = "钉钉通知@全体(是/否)"
PUSH_TG_TOKEN = "tgapi令牌"
PUSH_TG_CHAT_ID = "tg聊天id(个人或者群组id)"
PUSH_BARK_URL = "Bark推送地址"
PUSH_NTFY_URL = "ntfy推送地址"
PUSH_NTFY_TAGS = "ntfy标签"
PUSH_PUSHPLUS_TOKEN = "PushPlus令牌"
PUSH_EMAIL_HOST = "SMTP服务器"
PUSH_EMAIL_LOGIN = "邮箱账号"
PUSH_EMAIL_PASS = "邮箱密码"
PUSH_EMAIL_SENDER = "发件邮箱"
PUSH_EMAIL_SENDER_NAME = "发件人名称"
PUSH_EMAIL_TO = "收件邮箱"
PUSH_EMAIL_PORT = "SMTP端口"
PUSH_EMAIL_SSL = "SMTP启用SSL(是/否)"


class SettingsPage(QWidget):
    log_requested = Signal(str, str, str)
    status_requested = Signal(str, int)
    settings_saved = Signal(object)

    def __init__(
        self,
        viewmodel: SettingsViewModel | None = None,
        config_service: ConfigService | None = None,
        desktop_runtime_service: DesktopRuntimeService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.viewmodel = viewmodel or SettingsViewModel()
        self.config_service = config_service
        self.desktop_runtime_service = desktop_runtime_service
        self.output_dir_input = QLineEdit(self)
        self.output_format_combo = QComboBox(self)
        self.quality_combo = QComboBox(self)
        self.max_concurrency_spin = QSpinBox(self)
        self.loop_seconds_spin = QSpinBox(self)
        self.queue_seconds_spin = QSpinBox(self)
        self.disk_space_limit_spin = QDoubleSpinBox(self)
        self.split_checkbox = QCheckBox("启用分段录制", self)
        self.split_spin = QSpinBox(self)
        self.disable_record_checkbox = QCheckBox("仅通知不录制", self)
        self.use_https_recording_checkbox = QCheckBox("优先使用 HTTPS 录制源", self)
        self.folder_by_author_checkbox = QCheckBox("按主播分目录", self)
        self.folder_by_time_checkbox = QCheckBox("按日期分目录", self)
        self.folder_by_title_checkbox = QCheckBox("按直播标题分目录", self)
        self.filename_include_title_checkbox = QCheckBox("文件名包含直播标题", self)
        self.clean_emoji_checkbox = QCheckBox("清理文件名中的表情字符", self)
        self.show_source_url_checkbox = QCheckBox("显示直播源地址", self)
        self.convert_to_mp4_checkbox = QCheckBox("录制完成后自动转为 MP4", self)
        self.convert_to_h264_checkbox = QCheckBox("转码为 H.264", self)
        self.delete_origin_after_convert_checkbox = QCheckBox("转码后删除原文件", self)
        self.create_time_file_checkbox = QCheckBox("生成时间字幕文件", self)
        self.custom_script_input = QLineEdit(self)
        self.proxy_checkbox = QCheckBox("启用代理", self)
        self.proxy_input = QLineEdit(self)
        self.proxy_platforms_input = QLineEdit(self)
        self.extra_proxy_platforms_input = QLineEdit(self)
        self.notify_checkbox = QCheckBox("启用通知", self)
        self.notify_channels_input = QLineEdit(self)
        self.wechat_url_input = QLineEdit(self)
        self.wechat_test_button = QPushButton("发送测试通知", self)
        self.dingtalk_url_input = QLineEdit(self)
        self.dingtalk_phone_input = QLineEdit(self)
        self.dingtalk_at_all_checkbox = QCheckBox("钉钉@全体", self)
        self.dingtalk_test_button = QPushButton("发送测试通知", self)
        self.telegram_token_input = QLineEdit(self)
        self.telegram_chat_id_input = QLineEdit(self)
        self.telegram_test_button = QPushButton("发送测试通知", self)
        self.bark_url_input = QLineEdit(self)
        self.bark_test_button = QPushButton("发送测试通知", self)
        self.ntfy_url_input = QLineEdit(self)
        self.ntfy_tags_input = QLineEdit(self)
        self.ntfy_test_button = QPushButton("发送测试通知", self)
        self.pushplus_token_input = QLineEdit(self)
        self.pushplus_test_button = QPushButton("发送测试通知", self)
        self.email_host_input = QLineEdit(self)
        self.email_login_input = QLineEdit(self)
        self.email_password_input = QLineEdit(self)
        self.email_sender_input = QLineEdit(self)
        self.email_sender_name_input = QLineEdit(self)
        self.email_to_input = QLineEdit(self)
        self.email_port_input = QLineEdit(self)
        self.email_ssl_checkbox = QCheckBox("SMTP 启用 SSL", self)
        self.email_test_button = QPushButton("发送测试通知", self)
        self.douyin_cookie_input = QLineEdit(self)
        self.cookies_editor = QPlainTextEdit(self)
        self.authorization_editor = QPlainTextEdit(self)
        self.credentials_editor = QPlainTextEdit(self)
        self.minimize_to_tray_checkbox = QCheckBox("最小化时隐藏到系统托盘", self)
        self.close_to_tray_checkbox = QCheckBox("关闭窗口时转为托盘常驻", self)
        self.start_on_boot_checkbox = QCheckBox("开机自动启动客户端", self)
        self.restore_tasks_on_launch_checkbox = QCheckBox("异常退出后自动恢复上次运行中的任务", self)
        self.restore_window_on_launch_checkbox = QCheckBox("启动时恢复上次桌面状态", self)
        self._build_ui()
        self._load_from_viewmodel()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("客户端设置", self))
        toolbar.addStretch(1)

        save_button = QPushButton("保存设置", self)
        save_button.clicked.connect(self._save_settings)
        toolbar.addWidget(save_button)

        reset_button = QPushButton("重置界面", self)
        reset_button.clicked.connect(self._load_from_viewmodel)
        toolbar.addWidget(reset_button)
        root.addLayout(toolbar)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget(scroll)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        content_layout.addWidget(self._build_recording_group())
        content_layout.addWidget(self._build_output_group())
        content_layout.addWidget(self._build_postprocess_group())
        content_layout.addWidget(self._build_proxy_group())
        content_layout.addWidget(self._build_notification_group())
        content_layout.addWidget(self._build_cookies_group())
        content_layout.addWidget(self._build_advanced_auth_group())
        content_layout.addWidget(self._build_desktop_group())
        content_layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)
        self.split_checkbox.toggled.connect(self.split_spin.setEnabled)
        self.proxy_checkbox.toggled.connect(self._set_proxy_fields_enabled)
        self.notify_checkbox.toggled.connect(self._set_notification_fields_enabled)
        self.convert_to_mp4_checkbox.toggled.connect(self._set_convert_fields_enabled)

    def _build_recording_group(self) -> QGroupBox:
        group = QGroupBox("录制设置", self)
        form = QFormLayout(group)

        self.output_format_combo.addItems([fmt.value for fmt in OutputFormat])
        self.quality_combo.addItems(QUALITY_OPTIONS)
        self.output_dir_input.setPlaceholderText("例如：downloads 或 D:/Recordings")
        self.max_concurrency_spin.setRange(1, 32)
        self.loop_seconds_spin.setRange(5, 24 * 3600)
        self.loop_seconds_spin.setSuffix(" 秒")
        self.queue_seconds_spin.setRange(0, 3600)
        self.queue_seconds_spin.setSuffix(" 秒")
        self.split_spin.setRange(60, 24 * 3600)
        self.split_spin.setSuffix(" 秒")

        form.addRow("输出目录", self.output_dir_input)
        form.addRow("输出格式", self.output_format_combo)
        form.addRow("默认画质", self.quality_combo)
        form.addRow("并发任务数", self.max_concurrency_spin)
        form.addRow("巡检间隔", self.loop_seconds_spin)
        form.addRow("排队等待", self.queue_seconds_spin)
        form.addRow("", self.split_checkbox)
        form.addRow("分段时长", self.split_spin)
        form.addRow("", self.disable_record_checkbox)
        return group

    def _build_output_group(self) -> QGroupBox:
        group = QGroupBox("输出与目录", self)
        form = QFormLayout(group)
        self.disk_space_limit_spin.setRange(0.1, 1024.0)
        self.disk_space_limit_spin.setDecimals(1)
        self.disk_space_limit_spin.setSingleStep(0.5)
        self.disk_space_limit_spin.setSuffix(" GB")

        form.addRow("", self.use_https_recording_checkbox)
        form.addRow("", self.folder_by_author_checkbox)
        form.addRow("", self.folder_by_time_checkbox)
        form.addRow("", self.folder_by_title_checkbox)
        form.addRow("", self.filename_include_title_checkbox)
        form.addRow("", self.clean_emoji_checkbox)
        form.addRow("磁盘剩余阈值", self.disk_space_limit_spin)
        form.addRow("", self.show_source_url_checkbox)
        return group

    def _build_postprocess_group(self) -> QGroupBox:
        group = QGroupBox("后处理与脚本", self)
        form = QFormLayout(group)
        self.custom_script_input.setPlaceholderText("例如：python post_process.py")

        form.addRow("", self.convert_to_mp4_checkbox)
        form.addRow("", self.convert_to_h264_checkbox)
        form.addRow("", self.delete_origin_after_convert_checkbox)
        form.addRow("", self.create_time_file_checkbox)
        form.addRow("自定义脚本", self.custom_script_input)
        return group

    def _build_proxy_group(self) -> QGroupBox:
        group = QGroupBox("代理设置", self)
        form = QFormLayout(group)
        self.proxy_input.setPlaceholderText("例如：http://127.0.0.1:7890")
        self.proxy_platforms_input.setPlaceholderText("例如：tiktok.com, twitch.tv")
        self.extra_proxy_platforms_input.setPlaceholderText("例如：showroom-live.com, chzzk.naver.com")
        form.addRow("", self.proxy_checkbox)
        form.addRow("代理地址", self.proxy_input)
        form.addRow("代理平台", self.proxy_platforms_input)
        form.addRow("额外代理平台", self.extra_proxy_platforms_input)
        return group

    def _build_notification_group(self) -> QGroupBox:
        group = QGroupBox("通知设置", self)
        form = QFormLayout(group)
        self.notify_channels_input.setPlaceholderText("例如：微信、钉钉、Telegram")
        self.wechat_url_input.setPlaceholderText("例如：https://xizhi.qqoq.net/xxxx.send")
        self.dingtalk_url_input.setPlaceholderText("例如：https://oapi.dingtalk.com/robot/send?access_token=...")
        self.dingtalk_phone_input.setPlaceholderText("例如：13800138000")
        self.telegram_token_input.setPlaceholderText("例如：123456:ABCDEF...")
        self.telegram_chat_id_input.setPlaceholderText("例如：1000123456")
        self.bark_url_input.setPlaceholderText("例如：https://api.day.app/your_key")
        self.ntfy_url_input.setPlaceholderText("例如：https://ntfy.sh/your-topic")
        self.ntfy_tags_input.setPlaceholderText("例如：tada, bell")
        self.pushplus_token_input.setPlaceholderText("例如：your-pushplus-token")
        self.email_host_input.setPlaceholderText("例如：smtp.qq.com")
        self.email_login_input.setPlaceholderText("例如：your_account@qq.com")
        self.email_password_input.setPlaceholderText("请输入邮箱密码或授权码")
        self.email_password_input.setEchoMode(QLineEdit.Password)
        self.email_sender_input.setPlaceholderText("例如：your_account@qq.com")
        self.email_sender_name_input.setPlaceholderText("例如：DouyinLiveRecorder")
        self.email_to_input.setPlaceholderText("例如：user1@example.com,user2@example.com")
        self.email_port_input.setPlaceholderText("例如：465")
        self.wechat_test_button.clicked.connect(lambda: self._send_test_notification(CHANNEL_WECHAT))
        self.dingtalk_test_button.clicked.connect(lambda: self._send_test_notification(CHANNEL_DINGTALK))
        self.telegram_test_button.clicked.connect(lambda: self._send_test_notification(CHANNEL_TELEGRAM))
        self.bark_test_button.clicked.connect(lambda: self._send_test_notification(CHANNEL_BARK))
        self.ntfy_test_button.clicked.connect(lambda: self._send_test_notification(CHANNEL_NTFY))
        self.pushplus_test_button.clicked.connect(lambda: self._send_test_notification(CHANNEL_PUSHPLUS))
        self.email_test_button.clicked.connect(lambda: self._send_test_notification(CHANNEL_EMAIL))
        form.addRow("", self.notify_checkbox)
        form.addRow("通知渠道", self.notify_channels_input)
        form.addRow("微信接口", self._build_input_with_button(self.wechat_url_input, self.wechat_test_button))
        form.addRow("钉钉接口", self._build_input_with_button(self.dingtalk_url_input, self.dingtalk_test_button))
        form.addRow("钉钉@手机号", self.dingtalk_phone_input)
        form.addRow("", self.dingtalk_at_all_checkbox)
        form.addRow("Telegram Token", self.telegram_token_input)
        form.addRow("Telegram Chat ID", self._build_input_with_button(self.telegram_chat_id_input, self.telegram_test_button))
        form.addRow("Bark 地址", self._build_input_with_button(self.bark_url_input, self.bark_test_button))
        form.addRow("ntfy 地址", self._build_input_with_button(self.ntfy_url_input, self.ntfy_test_button))
        form.addRow("ntfy 标签", self.ntfy_tags_input)
        form.addRow("PushPlus 令牌", self._build_input_with_button(self.pushplus_token_input, self.pushplus_test_button))
        form.addRow("SMTP 服务器", self.email_host_input)
        form.addRow("邮箱账号", self.email_login_input)
        form.addRow("邮箱密码", self.email_password_input)
        form.addRow("发件邮箱", self.email_sender_input)
        form.addRow("发件人名称", self.email_sender_name_input)
        form.addRow("收件邮箱", self._build_input_with_button(self.email_to_input, self.email_test_button))
        form.addRow("SMTP 端口", self.email_port_input)
        form.addRow("", self.email_ssl_checkbox)
        return group

    def _build_cookies_group(self) -> QGroupBox:
        group = QGroupBox("登录凭证", self)
        form = QFormLayout(group)
        self.douyin_cookie_input.setPlaceholderText("请输入抖音登录凭证")
        form.addRow("抖音登录凭证", self.douyin_cookie_input)
        return group

    def _build_advanced_auth_group(self) -> QGroupBox:
        group = QGroupBox("高级配置", self)
        layout = QVBoxLayout(group)
        hint = QLabel(
            "按“键 = 值”格式填写，每行一项；可直接维护 Cookie、Authorization 和账号密码原始配置。",
            group,
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.cookies_editor.setPlaceholderText(
            "示例：\n抖音cookie = ttwid=...\nshowroom_cookie = ...\nchzzk_cookie = ..."
        )
        self.authorization_editor.setPlaceholderText(
            "示例：\npopkontv_token = your_token"
        )
        self.credentials_editor.setPlaceholderText(
            "示例：\nsooplive账号 = your_account\nsooplive密码 = your_password\npartner_code = P-00001"
        )

        form = QFormLayout()
        form.addRow("Cookie", self.cookies_editor)
        form.addRow("Authorization", self.authorization_editor)
        form.addRow("账号密码", self.credentials_editor)
        layout.addLayout(form)
        return group

    def _build_desktop_group(self) -> QGroupBox:
        group = QGroupBox("桌面与恢复", self)
        form = QFormLayout(group)
        form.addRow("", self.minimize_to_tray_checkbox)
        form.addRow("", self.close_to_tray_checkbox)
        form.addRow("", self.start_on_boot_checkbox)
        form.addRow("", self.restore_tasks_on_launch_checkbox)
        form.addRow("", self.restore_window_on_launch_checkbox)
        return group

    def _load_from_viewmodel(self) -> None:
        config = self.viewmodel.config
        self.output_dir_input.setText(str(config.output_dir))
        self.output_format_combo.setCurrentText(config.output_format.value)
        self.quality_combo.setCurrentText(config.quality)
        self.max_concurrency_spin.setValue(config.max_concurrency)
        self.loop_seconds_spin.setValue(config.loop_seconds)
        self.queue_seconds_spin.setValue(config.queue_seconds)
        self.split_checkbox.setChecked(config.split_recording)
        self.split_spin.setValue(config.split_seconds)
        self.disable_record_checkbox.setChecked(config.disable_record)
        self.use_https_recording_checkbox.setChecked(config.use_https_recording)
        self.folder_by_author_checkbox.setChecked(config.folder_by_author)
        self.folder_by_time_checkbox.setChecked(config.folder_by_time)
        self.folder_by_title_checkbox.setChecked(config.folder_by_title)
        self.filename_include_title_checkbox.setChecked(config.filename_include_title)
        self.clean_emoji_checkbox.setChecked(config.clean_emoji)
        self.disk_space_limit_spin.setValue(config.disk_space_limit_gb)
        self.show_source_url_checkbox.setChecked(config.show_source_url)
        self.convert_to_mp4_checkbox.setChecked(config.convert_to_mp4)
        self.convert_to_h264_checkbox.setChecked(config.convert_to_h264)
        self.delete_origin_after_convert_checkbox.setChecked(config.delete_origin_after_convert)
        self.create_time_file_checkbox.setChecked(config.create_time_file)
        self.custom_script_input.setText(config.custom_script)
        self.proxy_checkbox.setChecked(config.use_proxy)
        self.proxy_input.setText(config.proxy_url)
        self.proxy_platforms_input.setText(", ".join(config.proxy_platforms))
        self.extra_proxy_platforms_input.setText(", ".join(config.extra_proxy_platforms))
        self.notify_checkbox.setChecked(config.enable_notifications)
        self.notify_channels_input.setText(config.notify_channels)
        self.wechat_url_input.setText(self._push_setting(config, PUSH_WECHAT_URL))
        self.dingtalk_url_input.setText(self._push_setting(config, PUSH_DINGTALK_URL))
        self.dingtalk_phone_input.setText(self._push_setting(config, PUSH_DINGTALK_PHONE))
        self.dingtalk_at_all_checkbox.setChecked(self._push_setting(config, PUSH_DINGTALK_AT_ALL).strip().lower() in {"是", "true", "1", "yes", "on"})
        self.telegram_token_input.setText(self._push_setting(config, PUSH_TG_TOKEN))
        self.telegram_chat_id_input.setText(self._push_setting(config, PUSH_TG_CHAT_ID))
        self.bark_url_input.setText(self._push_setting(config, PUSH_BARK_URL))
        self.ntfy_url_input.setText(self._push_setting(config, PUSH_NTFY_URL))
        self.ntfy_tags_input.setText(self._push_setting(config, PUSH_NTFY_TAGS))
        self.pushplus_token_input.setText(self._push_setting(config, PUSH_PUSHPLUS_TOKEN))
        self.email_host_input.setText(self._push_setting(config, PUSH_EMAIL_HOST))
        self.email_login_input.setText(self._push_setting(config, PUSH_EMAIL_LOGIN))
        self.email_password_input.setText(self._push_setting(config, PUSH_EMAIL_PASS))
        self.email_sender_input.setText(self._push_setting(config, PUSH_EMAIL_SENDER))
        self.email_sender_name_input.setText(self._push_setting(config, PUSH_EMAIL_SENDER_NAME))
        self.email_to_input.setText(self._push_setting(config, PUSH_EMAIL_TO))
        self.email_port_input.setText(self._push_setting(config, PUSH_EMAIL_PORT))
        self.email_ssl_checkbox.setChecked(self._push_setting(config, PUSH_EMAIL_SSL).strip().lower() in {"是", "true", "1", "yes", "on"})
        self.douyin_cookie_input.setText(config.douyin_cookie)
        self.cookies_editor.setPlainText(self._format_key_values(config.cookies))
        self.authorization_editor.setPlainText(self._format_key_values(config.authorization))
        self.credentials_editor.setPlainText(self._format_key_values(config.credentials))
        self.minimize_to_tray_checkbox.setChecked(config.minimize_to_tray)
        self.close_to_tray_checkbox.setChecked(config.close_to_tray)
        self.start_on_boot_checkbox.setChecked(config.start_on_boot)
        self.restore_tasks_on_launch_checkbox.setChecked(config.restore_tasks_on_launch)
        self.restore_window_on_launch_checkbox.setChecked(config.restore_window_on_launch)
        self.split_spin.setEnabled(self.split_checkbox.isChecked())
        self._set_proxy_fields_enabled(self.proxy_checkbox.isChecked())
        self._set_notification_fields_enabled(self.notify_checkbox.isChecked())
        self._set_convert_fields_enabled(self.convert_to_mp4_checkbox.isChecked())
        self._emit_log("已从配置模型加载设置。", LEVEL_DEBUG)

    def _save_settings(self) -> None:
        config = self.viewmodel.config
        config.output_dir = Path(self.output_dir_input.text().strip() or "downloads")
        config.output_format = OutputFormat(self.output_format_combo.currentText())
        config.quality = self.quality_combo.currentText()
        config.max_concurrency = self.max_concurrency_spin.value()
        config.loop_seconds = self.loop_seconds_spin.value()
        config.queue_seconds = self.queue_seconds_spin.value()
        config.split_recording = self.split_checkbox.isChecked()
        config.split_seconds = self.split_spin.value()
        config.disable_record = self.disable_record_checkbox.isChecked()
        config.use_https_recording = self.use_https_recording_checkbox.isChecked()
        config.folder_by_author = self.folder_by_author_checkbox.isChecked()
        config.folder_by_time = self.folder_by_time_checkbox.isChecked()
        config.folder_by_title = self.folder_by_title_checkbox.isChecked()
        config.filename_include_title = self.filename_include_title_checkbox.isChecked()
        config.clean_emoji = self.clean_emoji_checkbox.isChecked()
        config.disk_space_limit_gb = self.disk_space_limit_spin.value()
        config.show_source_url = self.show_source_url_checkbox.isChecked()
        config.convert_to_mp4 = self.convert_to_mp4_checkbox.isChecked()
        config.convert_to_h264 = self.convert_to_h264_checkbox.isChecked()
        config.delete_origin_after_convert = self.delete_origin_after_convert_checkbox.isChecked()
        config.create_time_file = self.create_time_file_checkbox.isChecked()
        config.custom_script = self.custom_script_input.text().strip()
        config.use_proxy = self.proxy_checkbox.isChecked()
        config.proxy_url = self.proxy_input.text().strip()
        config.proxy_platforms = self._split_csv(self.proxy_platforms_input.text())
        config.extra_proxy_platforms = self._split_csv(self.extra_proxy_platforms_input.text())
        config.enable_notifications = self.notify_checkbox.isChecked()
        config.notify_channels = self.notify_channels_input.text().strip()
        cookies = self._parse_key_values(self.cookies_editor.toPlainText())
        douyin_cookie = self.douyin_cookie_input.text().strip()
        if douyin_cookie:
            cookies["抖音cookie"] = douyin_cookie
        config.cookies = cookies
        config.authorization = self._parse_key_values(self.authorization_editor.toPlainText())
        config.credentials = self._parse_key_values(self.credentials_editor.toPlainText())
        config.douyin_cookie = douyin_cookie or str(cookies.get("抖音cookie") or "")
        config.minimize_to_tray = self.minimize_to_tray_checkbox.isChecked()
        config.close_to_tray = self.close_to_tray_checkbox.isChecked()
        config.start_on_boot = self.start_on_boot_checkbox.isChecked()
        config.restore_tasks_on_launch = self.restore_tasks_on_launch_checkbox.isChecked()
        config.restore_window_on_launch = self.restore_window_on_launch_checkbox.isChecked()
        config.push_settings = {
            **config.push_settings,
            PUSH_WECHAT_URL: self.wechat_url_input.text().strip(),
            PUSH_DINGTALK_URL: self.dingtalk_url_input.text().strip(),
            PUSH_DINGTALK_PHONE: self.dingtalk_phone_input.text().strip(),
            PUSH_DINGTALK_AT_ALL: "是" if self.dingtalk_at_all_checkbox.isChecked() else "否",
            PUSH_TG_TOKEN: self.telegram_token_input.text().strip(),
            PUSH_TG_CHAT_ID: self.telegram_chat_id_input.text().strip(),
            PUSH_BARK_URL: self.bark_url_input.text().strip(),
            PUSH_NTFY_URL: self.ntfy_url_input.text().strip(),
            PUSH_NTFY_TAGS: self.ntfy_tags_input.text().strip(),
            PUSH_PUSHPLUS_TOKEN: self.pushplus_token_input.text().strip(),
            PUSH_EMAIL_HOST: self.email_host_input.text().strip(),
            PUSH_EMAIL_LOGIN: self.email_login_input.text().strip(),
            PUSH_EMAIL_PASS: self.email_password_input.text().strip(),
            PUSH_EMAIL_SENDER: self.email_sender_input.text().strip(),
            PUSH_EMAIL_SENDER_NAME: self.email_sender_name_input.text().strip(),
            PUSH_EMAIL_TO: self.email_to_input.text().strip(),
            PUSH_EMAIL_PORT: self.email_port_input.text().strip(),
            PUSH_EMAIL_SSL: "是" if self.email_ssl_checkbox.isChecked() else "否",
        }

        if self.config_service is None:
            self._emit_log("当前未连接配置服务，本次修改仅保存在内存中。", LEVEL_WARNING)
            self.status_requested.emit("未连接配置服务，设置未落盘。", 3000)
            return

        try:
            if self.desktop_runtime_service is not None:
                actual_enabled = self.desktop_runtime_service.apply_startup_setting(config.start_on_boot)
                config.start_on_boot = actual_enabled
                self.start_on_boot_checkbox.setChecked(actual_enabled)
            self.config_service.save(config)
            self._emit_log("已保存到本地配置文件。", LEVEL_INFO)
            self.settings_saved.emit(config)
            self.status_requested.emit("设置已保存到本地配置。", 3000)
        except Exception as exc:
            QMessageBox.warning(self, "保存失败", f"设置保存失败：{exc}")
            self._emit_log(f"保存配置失败: {exc}", LEVEL_ERROR)
            self.status_requested.emit("设置保存失败。", 3000)

    def _send_test_notification(self, channel: str) -> None:
        try:
            service = NotificationService(
                config=self._build_notification_config(),
                log_handler=lambda message, level=None, source=None: self.log_requested.emit(
                    message,
                    level or LEVEL_INFO,
                    source or SOURCE_NOTIFICATION,
                ),
            )
            result = service.send_test_notification(channel)
            if result is None:
                self.status_requested.emit("测试通知发送失败。", 3000)
                return
            self._emit_log(f"已发送 {self._channel_display_name(channel)} 测试通知请求。", LEVEL_INFO)
            self._show_test_result(result.message, success=result.ok)
            self.status_requested.emit(f"{self._channel_display_name(channel)} 测试通知已完成。", 3000)
        except Exception as exc:
            self._emit_log(f"{self._channel_display_name(channel)} 测试通知失败: {exc}", LEVEL_ERROR)
            self._show_test_result(f"{self._channel_display_name(channel)} 测试通知失败：{exc}", success=False)
            self.status_requested.emit(f"{self._channel_display_name(channel)} 测试通知失败。", 3000)

    def _set_notification_fields_enabled(self, enabled: bool) -> None:
        for widget in (
            self.notify_channels_input,
            self.wechat_url_input,
            self.wechat_test_button,
            self.dingtalk_url_input,
            self.dingtalk_phone_input,
            self.dingtalk_at_all_checkbox,
            self.dingtalk_test_button,
            self.telegram_token_input,
            self.telegram_chat_id_input,
            self.telegram_test_button,
            self.bark_url_input,
            self.bark_test_button,
            self.ntfy_url_input,
            self.ntfy_tags_input,
            self.ntfy_test_button,
            self.pushplus_token_input,
            self.pushplus_test_button,
            self.email_host_input,
            self.email_login_input,
            self.email_password_input,
            self.email_sender_input,
            self.email_sender_name_input,
            self.email_to_input,
            self.email_port_input,
            self.email_ssl_checkbox,
            self.email_test_button,
        ):
            widget.setEnabled(enabled)

    def _set_proxy_fields_enabled(self, enabled: bool) -> None:
        for widget in (self.proxy_input, self.proxy_platforms_input, self.extra_proxy_platforms_input):
            widget.setEnabled(enabled)

    def _set_convert_fields_enabled(self, enabled: bool) -> None:
        for widget in (self.convert_to_h264_checkbox, self.delete_origin_after_convert_checkbox):
            widget.setEnabled(enabled)

    def _push_setting(self, config, key: str) -> str:
        return str(config.push_settings.get(key) or "")

    def _split_csv(self, value: str) -> list[str]:
        return [item.strip().lower() for item in re.split(r"[,，\n]+", value) if item.strip()]

    def _parse_key_values(self, raw_text: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for raw_line in raw_text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", maxsplit=1)
            elif ":" in line:
                key, value = line.split(":", maxsplit=1)
            else:
                key, value = line, ""
            key = key.strip()
            if not key:
                continue
            result[key] = value.strip()
        return result

    def _format_key_values(self, values: dict[str, str]) -> str:
        if not values:
            return ""
        return "\n".join(f"{key} = {value}" for key, value in values.items())

    def _build_input_with_button(self, line_edit: QLineEdit, button: QPushButton) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(line_edit, 1)
        layout.addWidget(button)
        return container

    def _build_notification_config(self) -> AppConfig:
        return AppConfig(
            enable_notifications=True,
            notify_channels=self.notify_channels_input.text().strip(),
            push_settings={
                PUSH_WECHAT_URL: self.wechat_url_input.text().strip(),
                PUSH_DINGTALK_URL: self.dingtalk_url_input.text().strip(),
                PUSH_DINGTALK_PHONE: self.dingtalk_phone_input.text().strip(),
                PUSH_DINGTALK_AT_ALL: "是" if self.dingtalk_at_all_checkbox.isChecked() else "否",
                PUSH_TG_TOKEN: self.telegram_token_input.text().strip(),
                PUSH_TG_CHAT_ID: self.telegram_chat_id_input.text().strip(),
                PUSH_BARK_URL: self.bark_url_input.text().strip(),
                PUSH_NTFY_URL: self.ntfy_url_input.text().strip(),
                PUSH_NTFY_TAGS: self.ntfy_tags_input.text().strip(),
                PUSH_PUSHPLUS_TOKEN: self.pushplus_token_input.text().strip(),
                PUSH_EMAIL_HOST: self.email_host_input.text().strip(),
                PUSH_EMAIL_LOGIN: self.email_login_input.text().strip(),
                PUSH_EMAIL_PASS: self.email_password_input.text().strip(),
                PUSH_EMAIL_SENDER: self.email_sender_input.text().strip(),
                PUSH_EMAIL_SENDER_NAME: self.email_sender_name_input.text().strip(),
                PUSH_EMAIL_TO: self.email_to_input.text().strip(),
                PUSH_EMAIL_PORT: self.email_port_input.text().strip(),
                PUSH_EMAIL_SSL: "是" if self.email_ssl_checkbox.isChecked() else "否",
            },
        )

    def _channel_display_name(self, channel: str) -> str:
        return {
            CHANNEL_WECHAT: "微信",
            CHANNEL_DINGTALK: "钉钉",
            CHANNEL_TELEGRAM: "Telegram",
            CHANNEL_BARK: "Bark",
            CHANNEL_NTFY: "ntfy",
            CHANNEL_PUSHPLUS: "PushPlus",
            CHANNEL_EMAIL: "邮件",
        }.get(channel, channel)

    def _show_test_result(self, message: str, success: bool) -> None:
        title = "测试通知结果"
        if success:
            QMessageBox.information(self, title, message)
            return
        QMessageBox.warning(self, title, message)

    def _emit_log(self, message: str, level: str) -> None:
        self.log_requested.emit(message, level, SOURCE_SETTINGS)
