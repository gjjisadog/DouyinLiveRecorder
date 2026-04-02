from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path
import shutil
from unittest.mock import Mock, patch

from client.core.enums import OutputFormat, Platform, TaskStatus
from client.core.ffmpeg_service import FfmpegService
from client.core.models import AppConfig, RecordSession, RecordTask, StreamInfo
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
from client.core.record_worker import RecordWorker
from client.core.scheduler import Scheduler


class _FakeRecordManager:
    def __init__(self, tasks: dict[str, RecordTask] | None = None, start_side_effects: dict[str, Exception] | None = None) -> None:
        self.tasks = tasks or {}
        self.start_calls: list[str] = []
        self.sync_changed = False
        self._start_side_effects = start_side_effects or {}

    def sync_task_states(self) -> bool:
        return self.sync_changed

    def start_task(self, task_id: str) -> None:
        self.start_calls.append(task_id)
        exc = self._start_side_effects.get(task_id)
        if exc is not None:
            raise exc


class SchedulerTests(unittest.TestCase):
    def test_scheduler_starts_only_eligible_tasks(self) -> None:
        tasks = {
            "task-001": RecordTask(task_id="task-001", url="https://a", enabled=True, status=TaskStatus.IDLE),
            "task-002": RecordTask(task_id="task-002", url="https://b", enabled=False, status=TaskStatus.IDLE),
            "task-003": RecordTask(task_id="task-003", url="https://c", enabled=True, status=TaskStatus.RUNNING),
            "task-004": RecordTask(task_id="task-004", url="https://d", enabled=True, status=TaskStatus.STOPPED),
        }
        manager = _FakeRecordManager(tasks)
        scheduler = Scheduler(record_manager=manager, config=AppConfig(loop_seconds=30))
        now = datetime(2026, 3, 31, 12, 0, 0)

        scheduler.start(immediate=False)
        scheduler._next_run_at = now
        executed = scheduler.tick(now=now)

        self.assertTrue(executed)
        self.assertEqual(["task-001"], manager.start_calls)
        self.assertEqual(30, scheduler.seconds_until_next(now=now))

    def test_scheduler_marks_offline_and_failed_tasks(self) -> None:
        offline_task = RecordTask(task_id="task-011", url="https://offline", enabled=True, status=TaskStatus.IDLE)
        failed_task = RecordTask(task_id="task-012", url="https://failed", enabled=True, status=TaskStatus.IDLE)
        manager = _FakeRecordManager(
            {
                offline_task.task_id: offline_task,
                failed_task.task_id: failed_task,
            },
            start_side_effects={
                offline_task.task_id: RuntimeError("Task is not live: https://offline"),
                failed_task.task_id: RuntimeError("network boom"),
            },
        )
        scheduler = Scheduler(record_manager=manager, config=AppConfig(loop_seconds=30))

        scheduler.start(immediate=False)
        scheduler._next_run_at = datetime(2026, 3, 31, 12, 0, 0)
        scheduler.tick(now=datetime(2026, 3, 31, 12, 0, 0))

        self.assertIn("not live", offline_task.last_error.lower())
        self.assertEqual("network boom", failed_task.last_error)


class RecordWorkerTests(unittest.TestCase):
    def test_start_raises_for_offline_task_and_resets_status(self) -> None:
        resolver = Mock()
        resolver.resolve_task.return_value = StreamInfo(is_live=False, title="")
        ffmpeg_service = Mock()
        worker = RecordWorker(stream_resolver=resolver, ffmpeg_service=ffmpeg_service, config=AppConfig())
        task = RecordTask(task_id="task-101", url="https://live.douyin.com/123")

        with self.assertRaisesRegex(RuntimeError, "Task is not live"):
            worker.start(task)

        self.assertEqual(TaskStatus.IDLE, task.status)
        ffmpeg_service.build_command.assert_not_called()

    def test_start_records_session_and_history_for_live_task(self) -> None:
        stream = StreamInfo(is_live=True, title="直播标题", record_url="https://example.com/live.m3u8")
        session = RecordSession(
            task_id="task-102",
            started_at=datetime(2026, 3, 31, 12, 0, 0),
            process_id=1234,
            output_file=Path("downloads/test.ts"),
            command=["ffmpeg"],
        )
        resolver = Mock()
        resolver.resolve_task.return_value = stream
        ffmpeg_service = Mock()
        ffmpeg_service.build_command.return_value = (["ffmpeg"], Path("downloads/test.ts"))
        ffmpeg_service.start_record.return_value = session
        history = Mock()
        worker = RecordWorker(
            stream_resolver=resolver,
            ffmpeg_service=ffmpeg_service,
            config=AppConfig(),
            history_service=history,
        )
        task = RecordTask(task_id="task-102", url="https://live.douyin.com/456")

        result = worker.start(task)

        self.assertEqual(session, result)
        self.assertEqual(TaskStatus.RUNNING, task.status)
        self.assertEqual(Path("downloads/test.ts"), task.output_path)
        self.assertEqual("直播标题", task.title)
        self.assertIn(task.task_id, worker.sessions)
        history.record_started.assert_called_once_with(task, session)

    def test_sync_task_updates_completed_and_failed_statuses(self) -> None:
        resolver = Mock()
        ffmpeg_service = Mock()
        ffmpeg_service.is_session_over_size_limit.return_value = False
        history = Mock()
        worker = RecordWorker(
            stream_resolver=resolver,
            ffmpeg_service=ffmpeg_service,
            config=AppConfig(),
            history_service=history,
        )

        completed_task = RecordTask(task_id="task-103", url="https://a", status=TaskStatus.RUNNING)
        failed_task = RecordTask(task_id="task-104", url="https://b", status=TaskStatus.RUNNING)
        worker.sessions[completed_task.task_id] = RecordSession(task_id=completed_task.task_id, started_at=datetime.now())
        worker.sessions[failed_task.task_id] = RecordSession(task_id=failed_task.task_id, started_at=datetime.now())

        ffmpeg_service.poll_record.side_effect = [0, 2]

        self.assertTrue(worker.sync_task(completed_task))
        self.assertEqual(TaskStatus.COMPLETED, completed_task.status)
        history.record_finished.assert_any_call(completed_task, TaskStatus.COMPLETED)

        self.assertTrue(worker.sync_task(failed_task))
        self.assertEqual(TaskStatus.FAILED, failed_task.status)
        self.assertIn("code 2", failed_task.last_error)
        history.record_finished.assert_any_call(failed_task, TaskStatus.FAILED, failed_task.last_error)

    def test_sync_task_rolls_over_when_file_size_limit_is_hit(self) -> None:
        stream = StreamInfo(is_live=True, title="新分段", record_url="https://example.com/live.m3u8")
        old_session = RecordSession(
            task_id="task-105",
            started_at=datetime(2026, 3, 31, 12, 0, 0),
            process_id=1001,
            output_file=Path("downloads/old.ts"),
            command=["ffmpeg"],
        )
        new_session = RecordSession(
            task_id="task-105",
            started_at=datetime(2026, 3, 31, 12, 5, 0),
            process_id=1002,
            output_file=Path("downloads/new.ts"),
            command=["ffmpeg"],
        )
        resolver = Mock()
        resolver.resolve_task.return_value = stream
        ffmpeg_service = Mock()
        ffmpeg_service.is_session_over_size_limit.return_value = True
        ffmpeg_service.build_command.return_value = (["ffmpeg"], Path("downloads/new.ts"))
        ffmpeg_service.start_record.return_value = new_session
        history = Mock()
        worker = RecordWorker(
            stream_resolver=resolver,
            ffmpeg_service=ffmpeg_service,
            config=AppConfig(max_file_size_gb=1.0),
            history_service=history,
        )
        task = RecordTask(
            task_id="task-105",
            url="https://live.example.com/rollover",
            status=TaskStatus.RUNNING,
            output_path=Path("downloads/old.ts"),
            display_name="主播 A",
        )
        worker.sessions[task.task_id] = old_session

        changed = worker.sync_task(task)

        self.assertTrue(changed)
        ffmpeg_service.stop_record.assert_called_once_with(task)
        history.record_finished.assert_called_once_with(task, TaskStatus.COMPLETED)
        history.record_started.assert_called_once_with(task, new_session)
        self.assertEqual(TaskStatus.RUNNING, task.status)
        self.assertEqual(Path("downloads/new.ts"), task.output_path)
        self.assertEqual("新分段", task.title)
        self.assertEqual(new_session, worker.sessions[task.task_id])


class FfmpegServiceTests(unittest.TestCase):
    def test_build_command_applies_proxy_https_and_headers(self) -> None:
        service = FfmpegService()
        task = RecordTask(
            task_id="task-201",
            url="https://www.pandalive.co.kr/live/play/bara0109",
            platform=Platform.PANDATV,
            display_name="主播 A",
        )
        stream = StreamInfo(is_live=True, title="标题", record_url="http://example.com/live.m3u8")
        config = AppConfig(
            output_dir=Path("downloads"),
            output_format=OutputFormat.TS,
            use_proxy=True,
            proxy_url="http://127.0.0.1:7890",
            proxy_platforms=["pandalive.co.kr"],
            use_https_recording=True,
            split_recording=False,
        )

        command, output_file = service.build_command(task, stream, config)

        self.assertEqual("ffmpeg", command[0])
        self.assertIn("-http_proxy", command)
        self.assertIn("http://127.0.0.1:7890", command)
        self.assertIn("-headers", command)
        self.assertIn("origin:https://www.pandalive.co.kr", command)
        self.assertIn("https://example.com/live.m3u8", command)
        self.assertTrue(str(output_file).endswith(".ts"))

    def test_select_source_url_prefers_non_h265_flv_for_douyin(self) -> None:
        service = FfmpegService()
        task = RecordTask(task_id="task-202", url="https://live.douyin.com/1", platform=Platform.DOUYIN)
        stream = StreamInfo(
            is_live=True,
            flv_url="https://example.com/live.flv?codec=h264",
            m3u8_url="https://example.com/live.m3u8",
            record_url="https://example.com/live.m3u8",
        )

        selected = service.select_source_url(task, stream)

        self.assertEqual("https://example.com/live.flv?codec=h264", selected)

    def test_is_session_over_size_limit_checks_output_file_size(self) -> None:
        workspace = Path("tmp_ffmpeg_size_limit_test")
        workspace.mkdir(exist_ok=True)
        self.addCleanup(shutil.rmtree, workspace, True)
        output_file = workspace / "segment.ts"
        output_file.write_bytes(b"a" * 1024)
        session = RecordSession(
            task_id="task-203",
            started_at=datetime.now(),
            output_file=output_file,
        )
        service = FfmpegService()

        self.assertTrue(service.is_session_over_size_limit(session, AppConfig(max_file_size_gb=0.0000005)))
        self.assertFalse(service.is_session_over_size_limit(session, AppConfig(max_file_size_gb=1.0)))


class NotificationServiceTests(unittest.TestCase):
    def test_notify_sends_desktop_and_remote_channels(self) -> None:
        sender = Mock()
        config = AppConfig(
            enable_notifications=True,
            notify_channels="桌面, 微信, Telegram, Bark, ntfy, PushPlus, 邮件",
        )
        service = NotificationService(config=config, sender=sender)
        remote_calls: list[tuple[list[str], str, str]] = []
        service._notify_remote_channels = lambda channels, title, message: remote_calls.append((channels, title, message)) or []

        service.notify("标题", "内容")

        sender.assert_called_once_with("标题", "内容", "info")
        self.assertEqual(
            [(["wechat", "telegram", "bark", "ntfy", "pushplus", "email"], "标题", "内容")],
            remote_calls,
        )

    def test_send_test_notification_reports_missing_channel_configuration(self) -> None:
        service = NotificationService(config=AppConfig(enable_notifications=True))

        result = service.send_test_notification(CHANNEL_WECHAT)

        self.assertIsNotNone(result)
        self.assertEqual(CHANNEL_WECHAT, result.channel)
        self.assertFalse(result.ok)

    def test_remote_channel_result_messages_cover_success_and_failure(self) -> None:
        config = AppConfig(
            enable_notifications=True,
            push_settings={
                "微信推送接口链接": "https://xizhi.example/send",
                "钉钉推送接口链接": "https://dingtalk.example/send",
                "tgapi令牌": "token",
                "tg聊天id(个人或者群组id)": "123",
                "Bark推送地址": "https://bark.example/key",
                "ntfy推送地址": "https://ntfy.sh/topic",
                "PushPlus令牌": "pushplus-token",
                "SMTP服务器": "smtp.example.com",
                "邮箱账号": "sender@example.com",
                "邮箱密码": "secret",
                "发件邮箱": "sender@example.com",
                "发件人名称": "Recorder",
                "收件邮箱": "to@example.com",
                "SMTP端口": "465",
                "SMTP启用SSL(是/否)": "是",
            },
        )
        service = NotificationService(config=config)

        with (
            patch("client.core.notification_service.xizhi", return_value={"success": ["a"], "error": []}),
            patch("client.core.notification_service.dingtalk", return_value={"success": ["a"], "error": ["b"]}),
            patch("client.core.notification_service.tg_bot", return_value={"success": [], "error": ["x"]}),
            patch("client.core.notification_service.bark", return_value={"success": ["a"], "error": []}),
            patch("client.core.notification_service.ntfy", return_value={"success": ["a"], "error": []}),
            patch("client.core.notification_service.pushplus", return_value={"success": [], "error": ["x"]}),
            patch("client.core.notification_service.send_email", return_value={"success": ["to@example.com"], "error": []}),
        ):
            wechat = service.send_test_notification(CHANNEL_WECHAT)
            dingtalk = service.send_test_notification(CHANNEL_DINGTALK)
            telegram = service.send_test_notification(CHANNEL_TELEGRAM)
            bark_result = service.send_test_notification(CHANNEL_BARK)
            ntfy_result = service.send_test_notification(CHANNEL_NTFY)
            pushplus_result = service.send_test_notification(CHANNEL_PUSHPLUS)
            email_result = service.send_test_notification(CHANNEL_EMAIL)

        self.assertTrue(wechat.ok)
        self.assertIn("成功", wechat.message)
        self.assertFalse(dingtalk.ok)
        self.assertIn("部分成功", dingtalk.message)
        self.assertFalse(telegram.ok)
        self.assertIn("失败", telegram.message)
        self.assertTrue(bark_result.ok)
        self.assertTrue(ntfy_result.ok)
        self.assertFalse(pushplus_result.ok)
        self.assertTrue(email_result.ok)


if __name__ == "__main__":
    unittest.main()
