from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from client.core.enums import OutputFormat
from client.core.models import AppConfig
from client.ui.pages.settings_page import SettingsPage
from client.viewmodels.settings_viewmodel import SettingsViewModel
from client.ui.pages.settings_page import (
    PUSH_BARK_URL,
    PUSH_EMAIL_HOST,
    PUSH_EMAIL_LOGIN,
    PUSH_EMAIL_PASS,
    PUSH_EMAIL_PORT,
    PUSH_EMAIL_SENDER,
    PUSH_EMAIL_SENDER_NAME,
    PUSH_EMAIL_SSL,
    PUSH_EMAIL_TO,
    PUSH_NTFY_TAGS,
    PUSH_NTFY_URL,
    PUSH_PUSHPLUS_TOKEN,
)


class _FakeConfigService:
    def __init__(self) -> None:
        self.saved_configs: list[AppConfig] = []

    def save(self, config: AppConfig) -> None:
        self.saved_configs.append(config)


class _FakeDesktopRuntimeService:
    def __init__(self, actual_enabled: bool) -> None:
        self.actual_enabled = actual_enabled
        self.apply_calls: list[bool] = []

    def apply_startup_setting(self, enabled: bool) -> bool:
        self.apply_calls.append(enabled)
        return self.actual_enabled


class SettingsPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_settings_page_loads_extended_config_fields(self) -> None:
        config = AppConfig(
            output_dir=Path("records"),
            output_format=OutputFormat.MKV,
            quality="蓝光",
            max_concurrency=6,
            loop_seconds=900,
            queue_seconds=15,
            split_recording=False,
            split_seconds=2400,
            use_proxy=True,
            proxy_url="http://127.0.0.1:7890",
            use_https_recording=True,
            folder_by_author=False,
            folder_by_time=True,
            folder_by_title=True,
            filename_include_title=True,
            clean_emoji=False,
            disk_space_limit_gb=5.5,
            convert_to_mp4=False,
            convert_to_h264=True,
            delete_origin_after_convert=False,
            create_time_file=True,
            show_source_url=True,
            disable_record=True,
            custom_script="python hook.py",
            proxy_platforms=["tiktok.com", "twitch.tv"],
            extra_proxy_platforms=["showroom-live.com"],
            push_settings={
                PUSH_BARK_URL: "https://bark.example/key",
                PUSH_NTFY_URL: "https://ntfy.sh/topic",
                PUSH_NTFY_TAGS: "tada,bell",
                PUSH_PUSHPLUS_TOKEN: "pushplus-token",
                PUSH_EMAIL_HOST: "smtp.example.com",
                PUSH_EMAIL_LOGIN: "sender@example.com",
                PUSH_EMAIL_PASS: "secret",
                PUSH_EMAIL_SENDER: "sender@example.com",
                PUSH_EMAIL_SENDER_NAME: "Recorder",
                PUSH_EMAIL_TO: "to@example.com",
                PUSH_EMAIL_PORT: "465",
                PUSH_EMAIL_SSL: "是",
            },
            cookies={
                "抖音cookie": "dy_cookie_value",
                "showroom_cookie": "showroom_value",
            },
            authorization={
                "popkontv_token": "popkon-token",
            },
            credentials={
                "sooplive账号": "account_a",
                "sooplive密码": "password_a",
            },
            minimize_to_tray=False,
            close_to_tray=False,
            start_on_boot=True,
            restore_tasks_on_launch=False,
            restore_window_on_launch=False,
        )

        page = SettingsPage(viewmodel=SettingsViewModel(config=config))

        self.assertEqual("records", page.output_dir_input.text())
        self.assertEqual("mkv", page.output_format_combo.currentText())
        self.assertEqual("蓝光", page.quality_combo.currentText())
        self.assertEqual(1.0, page.max_file_size_spin.value())
        self.assertEqual(6, page.max_concurrency_spin.value())
        self.assertEqual(900, page.loop_seconds_spin.value())
        self.assertEqual(15, page.queue_seconds_spin.value())
        self.assertFalse(page.split_checkbox.isChecked())
        self.assertTrue(page.use_https_recording_checkbox.isChecked())
        self.assertFalse(page.folder_by_author_checkbox.isChecked())
        self.assertTrue(page.folder_by_time_checkbox.isChecked())
        self.assertTrue(page.folder_by_title_checkbox.isChecked())
        self.assertTrue(page.filename_include_title_checkbox.isChecked())
        self.assertFalse(page.clean_emoji_checkbox.isChecked())
        self.assertEqual(5.5, page.disk_space_limit_spin.value())
        self.assertFalse(page.convert_to_mp4_checkbox.isChecked())
        self.assertEqual("python hook.py", page.custom_script_input.text())
        self.assertEqual("tiktok.com, twitch.tv", page.proxy_platforms_input.text())
        self.assertEqual("showroom-live.com", page.extra_proxy_platforms_input.text())
        self.assertEqual("https://bark.example/key", page.bark_url_input.text())
        self.assertEqual("https://ntfy.sh/topic", page.ntfy_url_input.text())
        self.assertEqual("tada,bell", page.ntfy_tags_input.text())
        self.assertEqual("pushplus-token", page.pushplus_token_input.text())
        self.assertEqual("smtp.example.com", page.email_host_input.text())
        self.assertTrue(page.email_ssl_checkbox.isChecked())
        self.assertIn("抖音cookie = dy_cookie_value", page.cookies_editor.toPlainText())
        self.assertIn("showroom_cookie = showroom_value", page.cookies_editor.toPlainText())
        self.assertIn("popkontv_token = popkon-token", page.authorization_editor.toPlainText())
        self.assertIn("sooplive账号 = account_a", page.credentials_editor.toPlainText())
        self.assertFalse(page.minimize_to_tray_checkbox.isChecked())
        self.assertFalse(page.close_to_tray_checkbox.isChecked())
        self.assertTrue(page.start_on_boot_checkbox.isChecked())
        self.assertFalse(page.restore_tasks_on_launch_checkbox.isChecked())
        self.assertFalse(page.restore_window_on_launch_checkbox.isChecked())

    def test_settings_page_saves_extended_config_fields_back_to_viewmodel(self) -> None:
        config = AppConfig()
        page = SettingsPage(viewmodel=SettingsViewModel(config=config))

        page.output_dir_input.setText("D:/records")
        page.output_format_combo.setCurrentText("mp4")
        page.quality_combo.setCurrentText("超清")
        page.max_file_size_spin.setValue(0.8)
        page.max_concurrency_spin.setValue(8)
        page.loop_seconds_spin.setValue(120)
        page.queue_seconds_spin.setValue(9)
        page.split_checkbox.setChecked(True)
        page.split_spin.setValue(600)
        page.disable_record_checkbox.setChecked(True)
        page.use_https_recording_checkbox.setChecked(True)
        page.folder_by_author_checkbox.setChecked(False)
        page.folder_by_time_checkbox.setChecked(True)
        page.folder_by_title_checkbox.setChecked(True)
        page.filename_include_title_checkbox.setChecked(True)
        page.clean_emoji_checkbox.setChecked(False)
        page.disk_space_limit_spin.setValue(3.5)
        page.show_source_url_checkbox.setChecked(True)
        page.convert_to_mp4_checkbox.setChecked(True)
        page.convert_to_h264_checkbox.setChecked(True)
        page.delete_origin_after_convert_checkbox.setChecked(False)
        page.create_time_file_checkbox.setChecked(True)
        page.custom_script_input.setText("python after.py")
        page.proxy_checkbox.setChecked(True)
        page.proxy_input.setText("http://127.0.0.1:7890")
        page.proxy_platforms_input.setText("tiktok.com, Twitch.TV")
        page.extra_proxy_platforms_input.setText("showroom-live.com\nchzzk.naver.com")
        page.bark_url_input.setText("https://bark.example/key")
        page.ntfy_url_input.setText("https://ntfy.sh/topic")
        page.ntfy_tags_input.setText("tada,bell")
        page.pushplus_token_input.setText("pushplus-token")
        page.email_host_input.setText("smtp.example.com")
        page.email_login_input.setText("sender@example.com")
        page.email_password_input.setText("secret")
        page.email_sender_input.setText("sender@example.com")
        page.email_sender_name_input.setText("Recorder")
        page.email_to_input.setText("to@example.com")
        page.email_port_input.setText("465")
        page.email_ssl_checkbox.setChecked(True)
        page.douyin_cookie_input.setText("dy_cookie_value")
        page.cookies_editor.setPlainText("showroom_cookie = showroom_value\nchzzk_cookie: chzzk_value")
        page.authorization_editor.setPlainText("popkontv_token = popkon-token")
        page.credentials_editor.setPlainText("sooplive账号 = account_a\nsooplive密码 = password_a")
        page.minimize_to_tray_checkbox.setChecked(False)
        page.close_to_tray_checkbox.setChecked(False)
        page.start_on_boot_checkbox.setChecked(True)
        page.restore_tasks_on_launch_checkbox.setChecked(False)
        page.restore_window_on_launch_checkbox.setChecked(False)

        page._save_settings()

        self.assertEqual(Path("D:/records"), config.output_dir)
        self.assertEqual(OutputFormat.MP4, config.output_format)
        self.assertEqual("超清", config.quality)
        self.assertEqual(0.8, config.max_file_size_gb)
        self.assertEqual(8, config.max_concurrency)
        self.assertEqual(120, config.loop_seconds)
        self.assertEqual(9, config.queue_seconds)
        self.assertTrue(config.disable_record)
        self.assertTrue(config.use_https_recording)
        self.assertFalse(config.folder_by_author)
        self.assertTrue(config.folder_by_time)
        self.assertTrue(config.folder_by_title)
        self.assertTrue(config.filename_include_title)
        self.assertFalse(config.clean_emoji)
        self.assertEqual(3.5, config.disk_space_limit_gb)
        self.assertTrue(config.show_source_url)
        self.assertTrue(config.convert_to_mp4)
        self.assertTrue(config.convert_to_h264)
        self.assertFalse(config.delete_origin_after_convert)
        self.assertTrue(config.create_time_file)
        self.assertEqual("python after.py", config.custom_script)
        self.assertEqual(["tiktok.com", "twitch.tv"], config.proxy_platforms)
        self.assertEqual(["showroom-live.com", "chzzk.naver.com"], config.extra_proxy_platforms)
        self.assertEqual("https://bark.example/key", config.push_settings[PUSH_BARK_URL])
        self.assertEqual("https://ntfy.sh/topic", config.push_settings[PUSH_NTFY_URL])
        self.assertEqual("tada,bell", config.push_settings[PUSH_NTFY_TAGS])
        self.assertEqual("pushplus-token", config.push_settings[PUSH_PUSHPLUS_TOKEN])
        self.assertEqual("smtp.example.com", config.push_settings[PUSH_EMAIL_HOST])
        self.assertEqual("sender@example.com", config.push_settings[PUSH_EMAIL_LOGIN])
        self.assertEqual("secret", config.push_settings[PUSH_EMAIL_PASS])
        self.assertEqual("to@example.com", config.push_settings[PUSH_EMAIL_TO])
        self.assertEqual("465", config.push_settings[PUSH_EMAIL_PORT])
        self.assertEqual("是", config.push_settings[PUSH_EMAIL_SSL])
        self.assertEqual("dy_cookie_value", config.douyin_cookie)
        self.assertEqual("dy_cookie_value", config.cookies["抖音cookie"])
        self.assertEqual("showroom_value", config.cookies["showroom_cookie"])
        self.assertEqual("chzzk_value", config.cookies["chzzk_cookie"])
        self.assertEqual("popkon-token", config.authorization["popkontv_token"])
        self.assertEqual("account_a", config.credentials["sooplive账号"])
        self.assertEqual("password_a", config.credentials["sooplive密码"])
        self.assertFalse(config.minimize_to_tray)
        self.assertFalse(config.close_to_tray)
        self.assertTrue(config.start_on_boot)
        self.assertFalse(config.restore_tasks_on_launch)
        self.assertFalse(config.restore_window_on_launch)

    def test_settings_page_saves_actual_startup_state_after_runtime_apply(self) -> None:
        config = AppConfig()
        config_service = _FakeConfigService()
        desktop_runtime_service = _FakeDesktopRuntimeService(actual_enabled=False)
        page = SettingsPage(
            viewmodel=SettingsViewModel(config=config),
            config_service=config_service,
            desktop_runtime_service=desktop_runtime_service,
        )
        saved_configs: list[AppConfig] = []
        page.settings_saved.connect(saved_configs.append)

        page.start_on_boot_checkbox.setChecked(True)
        page._save_settings()

        self.assertEqual([True], desktop_runtime_service.apply_calls)
        self.assertEqual([config], config_service.saved_configs)
        self.assertFalse(config.start_on_boot)
        self.assertFalse(page.start_on_boot_checkbox.isChecked())
        self.assertEqual([config], saved_configs)


if __name__ == "__main__":
    unittest.main()
