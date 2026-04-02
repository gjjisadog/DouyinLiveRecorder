"""Application bootstrap helpers."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path

import PySide6


def _prepare_qt_runtime() -> None:
    pyside_dir = Path(PySide6.__file__).resolve().parent
    qt_bin_dir = pyside_dir / "Qt" / "bin"
    plugin_dir = pyside_dir / "plugins"
    if not plugin_dir.exists():
        plugin_dir = pyside_dir / "Qt" / "plugins"
    qml_dir = pyside_dir / "qml"
    if not qml_dir.exists():
        qml_dir = pyside_dir / "Qt" / "qml"

    dll_dirs: list[Path] = []
    for candidate in (qt_bin_dir, pyside_dir):
        if candidate.exists() and candidate not in dll_dirs:
            dll_dirs.append(candidate)

    path_parts = [str(path) for path in dll_dirs]
    current_path = os.environ.get("PATH", "")
    if current_path:
        path_parts.append(current_path)
    os.environ["PATH"] = os.pathsep.join(path_parts)

    if plugin_dir.exists():
        os.environ.setdefault("QT_PLUGIN_PATH", str(plugin_dir))
        platform_dir = plugin_dir / "platforms"
        if platform_dir.exists():
            os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(platform_dir))
    if qml_dir.exists():
        os.environ.setdefault("QML2_IMPORT_PATH", str(qml_dir))

    if hasattr(os, "add_dll_directory"):
        for dll_dir in dll_dirs:
            os.add_dll_directory(str(dll_dir))
        if plugin_dir.exists():
            os.add_dll_directory(str(plugin_dir))
            platform_dir = plugin_dir / "platforms"
            if platform_dir.exists():
                os.add_dll_directory(str(platform_dir))


_prepare_qt_runtime()

from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMessageBox

from client.app_settings import AppSettings
from client.core.config_service import ConfigService
from client.core.exceptions import DependencyMissingError
from client.core.ffmpeg_service import FfmpegService
from client.core.history_service import HistoryService
from client.core.notification_service import NotificationService
from client.core.record_manager import RecordManager
from client.core.record_worker import RecordWorker
from client.core.scheduler import Scheduler
from client.core.stream_resolver import StreamResolver
from client.core.task_persistence import TaskPersistenceService
from client.infra.env.dependency_checker import DependencyChecker
from client.infra.logging.log_service import LEVEL_INFO, LEVEL_WARNING, LogBuffer, LogHandler, SOURCE_SYSTEM
from client.infra.process.automation_bridge import AutomationBridge
from client.infra.process.desktop_runtime import DesktopRuntimeService, build_startup_command
from client.infra.storage.storage_strategy import StorageStrategyService
from client.ui.main_window import MainWindow
from client.viewmodels.settings_viewmodel import SettingsViewModel
from client.viewmodels.task_viewmodel import TaskViewModel


def _prompt_continue_without_ffmpeg(title: str, message: str) -> bool:
    result = QMessageBox.warning(
        None,
        title,
        message,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes,
    )
    return result == QMessageBox.Yes


def _ensure_runtime_dependencies(
    checker: DependencyChecker | None = None,
    prompt_continue: Callable[[str, str], bool] | None = None,
    log_handler: LogHandler | None = None,
) -> bool:
    dependency_checker = checker or DependencyChecker()
    prompt = prompt_continue or _prompt_continue_without_ffmpeg

    try:
        ffmpeg_path = dependency_checker.ensure_ffmpeg()
        if log_handler is not None:
            log_handler(f"启动检查通过：已检测到 ffmpeg（{ffmpeg_path}）。", LEVEL_INFO, SOURCE_SYSTEM)
        return True
    except DependencyMissingError as exc:
        message = (
            "未检测到 ffmpeg，客户端仍可继续打开并修改配置，但暂时无法开始录制。\n\n"
            "请先安装 ffmpeg，并确保命令行可以直接执行 `ffmpeg`。\n\n"
            f"详细信息：{exc}\n\n"
            "是否仍要继续打开客户端？"
        )
        if log_handler is not None:
            log_handler(f"启动检查未通过：{exc}", LEVEL_WARNING, SOURCE_SYSTEM)
        return prompt("缺少录制依赖", message)


def _initialize_storage_strategy(settings: AppSettings, log_handler: LogHandler | None = None) -> dict:
    storage_strategy = StorageStrategyService(
        manifest_path=settings.storage_meta_path,
        database_path=settings.database_path,
        log_handler=log_handler,
    )
    manifest = storage_strategy.ensure_initialized()
    if log_handler is not None:
        log_handler(
            f"客户端存储策略已确认：{manifest.get('mode', 'unknown')}",
            LEVEL_INFO,
            SOURCE_SYSTEM,
        )
    return manifest


def run() -> int:
    settings = AppSettings.load()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(settings.app_name)
    app.setApplicationVersion(settings.app_version)
    app.setOrganizationName(settings.organization_name)

    startup_log_buffer = LogBuffer()
    if not _ensure_runtime_dependencies(log_handler=startup_log_buffer.handle):
        return 0
    _initialize_storage_strategy(settings, log_handler=startup_log_buffer.handle)

    config_service = ConfigService(local_config_path=settings.config_path, log_handler=startup_log_buffer.handle)
    app_config = config_service.load()
    desktop_runtime_service = DesktopRuntimeService(
        runtime_state_path=settings.runtime_state_path,
        startup_name=settings.app_name,
        startup_command=build_startup_command(),
        log_handler=startup_log_buffer.handle,
    )
    startup_state = desktop_runtime_service.mark_launch_started()
    app_config.start_on_boot = desktop_runtime_service.is_startup_enabled()
    _, legacy_tasks = config_service.load_legacy()
    notification_service = NotificationService(config=app_config, log_handler=startup_log_buffer.handle)
    history_service = HistoryService(
        settings.history_path,
        log_handler=startup_log_buffer.handle,
        notification_service=notification_service,
    )
    task_persistence = TaskPersistenceService(
        settings.tasks_path,
        platform_router=config_service.platform_router,
        log_handler=startup_log_buffer.handle,
    )
    tasks = task_persistence.load_tasks(seed_tasks=legacy_tasks)
    stream_resolver = StreamResolver()
    ffmpeg_service = FfmpegService()
    record_worker = RecordWorker(
        stream_resolver=stream_resolver,
        ffmpeg_service=ffmpeg_service,
        config=app_config,
        history_service=history_service,
    )
    record_manager = RecordManager(worker=record_worker, config=app_config)
    scheduler = Scheduler(record_manager=record_manager, config=app_config)
    for task in tasks:
        record_manager.add_task(task)

    window = MainWindow(
        settings=settings,
        task_viewmodel=TaskViewModel(tasks=tasks),
        settings_viewmodel=SettingsViewModel(config=app_config),
        record_manager=record_manager,
        task_persistence=task_persistence,
        config_service=config_service,
        history_service=history_service,
        notification_service=notification_service,
        scheduler=scheduler,
        desktop_runtime_service=desktop_runtime_service,
        startup_state=startup_state,
    )
    app.aboutToQuit.connect(window._shutdown_for_exit)
    automation_bridge = AutomationBridge.from_env(handler=window, log_handler=window.logs_page.append_log)
    if automation_bridge is not None:
        automation_bridge.start(app)
        window.attach_automation_bridge(automation_bridge)
    startup_log_buffer.flush_to(window.logs_page.append_log)
    window.show()
    return app.exec()
