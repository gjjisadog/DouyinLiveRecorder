"""Main window for the desktop client."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMenu,
    QStatusBar,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
    QToolBar,
    QWidget,
)

from client.app_settings import AppSettings
from client.core.config_service import ConfigService
from client.core.enums import TaskStatus
from client.core.history_service import HistoryService
from client.core.models import AppConfig
from client.core.notification_service import NotificationService
from client.core.record_manager import RecordManager
from client.core.scheduler import Scheduler
from client.core.task_persistence import TaskPersistenceService
from client.infra.logging.log_service import LEVEL_ERROR, LEVEL_INFO, LEVEL_WARNING, SOURCE_MAIN_WINDOW
from client.infra.process.desktop_runtime import DesktopRuntimeService, DesktopRuntimeState
from client.ui.pages.history_page import HistoryPage
from client.ui.pages.logs_page import LogsPage
from client.ui.pages.settings_page import SettingsPage
from client.ui.pages.tasks_page import TasksPage
from client.viewmodels.settings_viewmodel import SettingsViewModel
from client.viewmodels.task_viewmodel import TaskViewModel


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: AppSettings,
        task_viewmodel: TaskViewModel | None = None,
        settings_viewmodel: SettingsViewModel | None = None,
        record_manager: RecordManager | None = None,
        task_persistence: TaskPersistenceService | None = None,
        config_service: ConfigService | None = None,
        history_service: HistoryService | None = None,
        notification_service: NotificationService | None = None,
        scheduler: Scheduler | None = None,
        desktop_runtime_service: DesktopRuntimeService | None = None,
        startup_state: DesktopRuntimeState | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.record_manager = record_manager
        self.task_persistence = task_persistence
        self.config_service = config_service
        self.history_service = history_service
        self.notification_service = notification_service
        self.scheduler = scheduler
        self.desktop_runtime_service = desktop_runtime_service
        self.startup_state = startup_state or DesktopRuntimeState()
        self.tabs = QTabWidget(self)
        self.scheduler_status_label = QLabel(self)
        self._app_icon = self._load_app_icon()
        self._tray_icon: QSystemTrayIcon | None = None
        self._tray_menu: QMenu | None = None
        self._tray_restore_action: QAction | None = None
        self._tray_toggle_visibility_action: QAction | None = None
        self._tray_exit_action: QAction | None = None
        self.scheduler_toggle_action: QAction | None = None
        self.scheduler_trigger_action: QAction | None = None
        self._allow_close = False
        self._shutdown_completed = False
        self._tray_message_shown = False
        self._scheduler_timer = QTimer(self)
        self._scheduler_timer.setInterval(1000)
        self._scheduler_timer.timeout.connect(self._on_scheduler_timer)
        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(2000)
        self._runtime_timer.timeout.connect(self._save_runtime_snapshot)
        self.tasks_page = TasksPage(
            viewmodel=task_viewmodel,
            record_manager=record_manager,
            task_persistence=task_persistence,
            parent=self,
        )
        self.settings_page = SettingsPage(
            viewmodel=settings_viewmodel,
            config_service=config_service,
            desktop_runtime_service=desktop_runtime_service,
            parent=self,
        )
        self.history_page = HistoryPage(history_service=history_service, parent=self)
        self.logs_page = LogsPage(self)
        self._build_ui()
        self._wire_signals()
        self._setup_notifications()
        self._apply_startup_state()
        self._append_log("主窗口已初始化。", LEVEL_INFO)
        self._append_log(f"已加载 {len(self.tasks_page.viewmodel.tasks)} 个任务。", LEVEL_INFO)

    def _build_ui(self) -> None:
        self.setWindowTitle(f"{self.settings.app_name} {self.settings.app_version}")
        self.resize(self.settings.window_width, self.settings.window_height)
        self.setMinimumSize(1024, 720)
        if not self._app_icon.isNull():
            self.setWindowIcon(self._app_icon)

        toolbar = QToolBar("主工具栏", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        for text, handler in (
            ("全部启动", self._log_start_all),
            ("全部停止", self._log_stop_all),
            ("保存设置", self.settings_page._save_settings),
        ):
            action = QAction(text, self)
            action.triggered.connect(handler)
            toolbar.addAction(action)

        toolbar.addSeparator()
        self.scheduler_toggle_action = QAction("暂停巡检", self)
        self.scheduler_toggle_action.triggered.connect(self._toggle_scheduler)
        toolbar.addAction(self.scheduler_toggle_action)

        self.scheduler_trigger_action = QAction("立即巡检", self)
        self.scheduler_trigger_action.triggered.connect(self._trigger_scheduler_now)
        toolbar.addAction(self.scheduler_trigger_action)

        toolbar.addSeparator()
        title_label = QLabel(f"{self.settings.product_name} {self.settings.app_version}", self)
        title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        toolbar.addWidget(title_label)
        toolbar.addSeparator()
        self.scheduler_status_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        toolbar.addWidget(self.scheduler_status_label)

        self.tabs.addTab(self.tasks_page, "任务")
        self.tabs.addTab(self.settings_page, "设置")
        self.tabs.addTab(self.history_page, "历史")
        self.tabs.addTab(self.logs_page, "日志")
        self.setCentralWidget(self.tabs)

        status_bar = QStatusBar(self)
        status_bar.showMessage("客户端已就绪，核心服务已连接。")
        self.setStatusBar(status_bar)

    def _wire_signals(self) -> None:
        self.tasks_page.log_requested.connect(self.logs_page.append_log)
        self.tasks_page.status_requested.connect(self.statusBar().showMessage)
        self.settings_page.log_requested.connect(self.logs_page.append_log)
        self.settings_page.status_requested.connect(self.statusBar().showMessage)
        self.settings_page.settings_saved.connect(self._on_settings_saved)
        self.history_page.log_requested.connect(self.logs_page.append_log)
        self.history_page.status_requested.connect(self.statusBar().showMessage)
        self.logs_page.status_requested.connect(self.statusBar().showMessage)
        if self.record_manager is not None:
            self.record_manager.set_log_handler(self.logs_page.append_log)
        if self.config_service is not None:
            self.config_service.set_log_handler(self.logs_page.append_log)
        if self.task_persistence is not None:
            self.task_persistence.set_log_handler(self.logs_page.append_log)
        if self.history_service is not None:
            self.history_service.set_log_handler(self.logs_page.append_log)
        if self.notification_service is not None:
            self.notification_service.set_log_handler(self.logs_page.append_log)
        if self.scheduler is not None:
            self.scheduler.set_log_handler(self.logs_page.append_log)
            if not self.scheduler.running:
                self.scheduler.start(immediate=True)
            self._scheduler_timer.start()
        if self.desktop_runtime_service is not None:
            self._runtime_timer.start()
        self._update_scheduler_ui()

    def _log_start_all(self) -> None:
        if self.record_manager is None:
            self._append_log("请求全部启动，但当前没有连接录制管理器。", LEVEL_WARNING)
            self.statusBar().showMessage("未连接录制管理器。", 3000)
            return
        try:
            self.record_manager.start_all()
            self._append_log("已执行全部启动。", LEVEL_INFO)
            self.tasks_page.refresh_table()
            self.statusBar().showMessage("已完成全部启动。", 3000)
        except Exception as exc:
            self._append_log(f"全部启动失败: {exc}", LEVEL_ERROR)
            self.tasks_page.refresh_table()
            self.statusBar().showMessage("全部启动失败。", 3000)

    def _log_stop_all(self) -> None:
        if self.record_manager is None:
            self._append_log("请求全部停止，但当前没有连接录制管理器。", LEVEL_WARNING)
            self.statusBar().showMessage("未连接录制管理器。", 3000)
            return
        try:
            self.record_manager.stop_all()
            self._append_log("已执行全部停止。", LEVEL_INFO)
            self.tasks_page.refresh_table()
            self.statusBar().showMessage("已完成全部停止。", 3000)
        except Exception as exc:
            self._append_log(f"全部停止失败: {exc}", LEVEL_ERROR)
            self.tasks_page.refresh_table()
            self.statusBar().showMessage("全部停止失败。", 3000)

    def _append_log(self, message: str, level: str) -> None:
        self.logs_page.append_log(message, level, SOURCE_MAIN_WINDOW)

    def _setup_notifications(self) -> None:
        if QSystemTrayIcon.isSystemTrayAvailable():
            tray_icon = self._app_icon if not self._app_icon.isNull() else self.style().standardIcon(QStyle.SP_ComputerIcon)
            self._tray_icon = QSystemTrayIcon(tray_icon, self)
            self._tray_icon.setToolTip(f"{self.settings.app_name} {self.settings.app_version}")
            self._tray_menu = QMenu(self)
            self._tray_restore_action = self._tray_menu.addAction("显示主窗口")
            self._tray_restore_action.triggered.connect(self._restore_from_tray)
            self._tray_toggle_visibility_action = self._tray_menu.addAction("隐藏到托盘")
            self._tray_toggle_visibility_action.triggered.connect(self._toggle_tray_visibility)
            self._tray_menu.addSeparator()
            self._tray_exit_action = self._tray_menu.addAction("退出客户端")
            self._tray_exit_action.triggered.connect(self._quit_from_tray)
            self._tray_icon.setContextMenu(self._tray_menu)
            self._tray_icon.activated.connect(self._handle_tray_activated)
            self._tray_icon.show()
            if self.notification_service is not None:
                self.notification_service.set_sender(self._show_tray_notification)
            self._update_tray_actions()
            return
        if self.notification_service is not None:
            self.notification_service.set_sender(self._show_status_notification)

    def _show_tray_notification(self, title: str, message: str, level: str) -> None:
        if self._tray_icon is None:
            self._show_status_notification(title, message, level)
            return
        icon = QSystemTrayIcon.Information
        if level == LEVEL_WARNING:
            icon = QSystemTrayIcon.Warning
        elif level == LEVEL_ERROR:
            icon = QSystemTrayIcon.Critical
        self._tray_icon.showMessage(title, message, icon, 5000)
        self.statusBar().showMessage(f"{title}：{message}", 5000)

    def _on_settings_saved(self, config: AppConfig) -> None:
        _ = config
        self._update_tray_actions()
        self._append_log("桌面常驻配置已更新。", LEVEL_INFO)
        if self.desktop_runtime_service is not None:
            self._save_runtime_snapshot()

    def _show_status_notification(self, title: str, message: str, level: str) -> None:
        _ = level
        self.statusBar().showMessage(f"{title}：{message}", 5000)

    def _toggle_scheduler(self) -> None:
        if self.scheduler is None:
            self.statusBar().showMessage("当前未连接自动巡检调度器。", 2500)
            return
        if self.scheduler.running:
            self.scheduler.stop()
            self.statusBar().showMessage("自动巡检已暂停。", 2500)
        else:
            self.scheduler.start(immediate=True)
            self.statusBar().showMessage("自动巡检已恢复。", 2500)
        self._update_scheduler_ui()

    def _trigger_scheduler_now(self) -> None:
        if self.scheduler is None:
            self.statusBar().showMessage("当前未连接自动巡检调度器。", 2500)
            return
        self.scheduler.trigger_now()
        self._on_scheduler_timer()
        self.statusBar().showMessage("已立即执行一次自动巡检。", 2500)

    def _on_scheduler_timer(self) -> None:
        if self.scheduler is None:
            self._update_scheduler_ui()
            return
        if self.scheduler.tick():
            self.tasks_page.refresh_table()
        self._update_scheduler_ui()

    def _update_scheduler_ui(self) -> None:
        if self.scheduler is None:
            self.scheduler_status_label.setText("自动巡检：未启用")
            if self.scheduler_toggle_action is not None:
                self.scheduler_toggle_action.setEnabled(False)
            if self.scheduler_trigger_action is not None:
                self.scheduler_trigger_action.setEnabled(False)
            return

        remaining = self.scheduler.seconds_until_next()
        if self.scheduler.running:
            if self.scheduler_toggle_action is not None:
                self.scheduler_toggle_action.setText("暂停巡检")
            countdown = f"{remaining}s" if remaining is not None else "-"
            self.scheduler_status_label.setText(f"自动巡检：运行中（{countdown}）")
        else:
            if self.scheduler_toggle_action is not None:
                self.scheduler_toggle_action.setText("恢复巡检")
            self.scheduler_status_label.setText("自动巡检：已暂停")

        if self.scheduler_trigger_action is not None:
            self.scheduler_trigger_action.setEnabled(True)

    def _load_app_icon(self) -> QIcon:
        if self.settings.icon_svg_path.exists():
            return QIcon(str(self.settings.icon_svg_path))
        return QIcon()

    def _handle_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick}:
            self._toggle_tray_visibility()

    def _toggle_tray_visibility(self) -> None:
        if self.isVisible() and not self.isMinimized():
            self._hide_to_tray(show_message=False)
            return
        self._restore_from_tray()

    def _restore_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.statusBar().showMessage("客户端已从系统托盘恢复。", 2500)
        self._update_tray_actions()
        self._save_runtime_snapshot()

    def _quit_from_tray(self) -> None:
        self._allow_close = True
        self.close()

    def _hide_to_tray(self, *, show_message: bool) -> None:
        self.hide()
        self._update_tray_actions()
        self._save_runtime_snapshot()
        if show_message and self._tray_icon is not None and not self._tray_message_shown:
            self._tray_icon.showMessage(
                self.settings.app_name,
                "客户端已转入系统托盘，双击托盘图标可恢复窗口。",
                QSystemTrayIcon.Information,
                4000,
            )
            self._tray_message_shown = True

    def _update_tray_actions(self) -> None:
        if self._tray_toggle_visibility_action is not None:
            self._tray_toggle_visibility_action.setText("显示主窗口" if not self.isVisible() else "隐藏到托盘")
        if self._tray_restore_action is not None:
            self._tray_restore_action.setEnabled(not self.isVisible())

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._allow_close and self._should_close_to_tray():
            event.ignore()
            self._hide_to_tray(show_message=True)
            return

        self._shutdown_for_exit()
        super().closeEvent(event)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() != QEvent.WindowStateChange:
            return
        if self.isMinimized() and self._should_minimize_to_tray():
            QTimer.singleShot(0, lambda: self._hide_to_tray(show_message=not self._tray_message_shown))

    def _should_close_to_tray(self) -> bool:
        return self._tray_icon is not None and self.settings_page.viewmodel.config.close_to_tray

    def _should_minimize_to_tray(self) -> bool:
        return self._tray_icon is not None and self.settings_page.viewmodel.config.minimize_to_tray

    def _should_start_hidden_on_launch(self, config: AppConfig) -> bool:
        return (
            self._tray_icon is not None
            and config.restore_window_on_launch
            and self.startup_state.hidden_to_tray
        )

    def _apply_startup_state(self) -> None:
        config = self.settings_page.viewmodel.config
        if config.restore_window_on_launch:
            self.tabs.setCurrentIndex(min(self.startup_state.current_tab_index, self.tabs.count() - 1))
            if self._should_start_hidden_on_launch(config):
                QTimer.singleShot(0, lambda: self._hide_to_tray(show_message=False))
        if self.scheduler is not None and not self.startup_state.scheduler_running:
            self.scheduler.stop()
            self._update_scheduler_ui()
        if self.startup_state.last_exit_clean:
            return
        if config.restore_tasks_on_launch:
            QTimer.singleShot(0, self._restore_interrupted_tasks)

    def _restore_interrupted_tasks(self) -> None:
        if self.record_manager is None:
            return
        restored = 0
        skipped = 0
        for task_id in self.startup_state.running_task_ids:
            task = self.record_manager.get_task(task_id)
            if task is None or not task.enabled:
                skipped += 1
                continue
            try:
                self.record_manager.start_task(task_id)
                restored += 1
            except Exception as exc:
                task.last_error = str(exc)
                skipped += 1
                self._append_log(f"恢复任务 {task_id} 失败: {exc}", LEVEL_WARNING)
        if restored or skipped:
            self.tasks_page.refresh_table()
            self._append_log(f"已尝试恢复上次运行中的任务：成功 {restored}，跳过 {skipped}。", LEVEL_INFO)

    def _build_runtime_state(self, *, last_exit_clean: bool) -> DesktopRuntimeState:
        running_task_ids: list[str] = []
        if self.record_manager is not None:
            running_task_ids = [
                task.task_id
                for task in self.record_manager.tasks.values()
                if task.status in {TaskStatus.PENDING, TaskStatus.RUNNING}
            ]
        return DesktopRuntimeState(
            last_exit_clean=last_exit_clean,
            running_task_ids=running_task_ids,
            scheduler_running=self.scheduler.running if self.scheduler is not None else False,
            current_tab_index=self.tabs.currentIndex(),
            hidden_to_tray=not self.isVisible(),
        )

    def _save_runtime_snapshot(self) -> None:
        if self.desktop_runtime_service is None:
            return
        self.desktop_runtime_service.save_state(self._build_runtime_state(last_exit_clean=False))

    def _shutdown_for_exit(self) -> None:
        if self._shutdown_completed:
            return
        self._shutdown_completed = True
        if self.desktop_runtime_service is not None:
            self.desktop_runtime_service.mark_clean_exit(self._build_runtime_state(last_exit_clean=True))
        if self._tray_icon is not None:
            self._tray_icon.hide()
