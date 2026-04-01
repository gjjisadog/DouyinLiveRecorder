"""Tasks page UI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from client.core.enums import Platform, TaskStatus
from client.core.models import RecordTask
from client.core.record_manager import RecordManager
from client.core.task_persistence import TaskPersistenceService
from client.infra.logging.log_service import LEVEL_DEBUG, LEVEL_WARNING, SOURCE_TASKS
from client.ui.dialogs.task_editor_dialog import TaskEditorDialog
from client.viewmodels.task_viewmodel import TaskActionResult, TaskViewModel

STATUS_LABELS: dict[TaskStatus, str] = {
    TaskStatus.IDLE: "空闲",
    TaskStatus.PENDING: "准备中",
    TaskStatus.RUNNING: "运行中",
    TaskStatus.STOPPED: "已停止",
    TaskStatus.COMPLETED: "已完成",
    TaskStatus.FAILED: "失败",
}

PLATFORM_LABELS: dict[Platform, str] = {
    Platform.UNKNOWN: "未知",
    Platform.DIRECT: "直链",
    Platform.DOUYIN: "抖音",
    Platform.TIKTOK: "TikTok",
    Platform.KUAISHOU: "快手",
    Platform.HUYA: "虎牙",
    Platform.DOUYU: "斗鱼",
    Platform.YY: "YY",
    Platform.BILIBILI: "Bilibili",
    Platform.NETEASE_CC: "网易CC",
    Platform.QIANDUREBO: "千度热播",
    Platform.PANDATV: "PandaTV",
    Platform.BAIDU: "百度直播",
    Platform.SHOWROOM: "ShowRoom",
    Platform.CHZZK: "CHZZK",
}

STATUS_BADGE_STYLES: dict[TaskStatus, tuple[str, str]] = {
    TaskStatus.IDLE: ("#E5E7EB", "#374151"),
    TaskStatus.PENDING: ("#FED7AA", "#9A3412"),
    TaskStatus.RUNNING: ("#BBF7D0", "#166534"),
    TaskStatus.STOPPED: ("#E2E8F0", "#475569"),
    TaskStatus.COMPLETED: ("#BFDBFE", "#1D4ED8"),
    TaskStatus.FAILED: ("#FECACA", "#B91C1C"),
}

ROW_HIGHLIGHT_COLORS: dict[TaskStatus, QColor] = {
    TaskStatus.PENDING: QColor("#FFF7ED"),
    TaskStatus.RUNNING: QColor("#ECFDF3"),
    TaskStatus.FAILED: QColor("#FEF2F2"),
}


class TasksPage(QWidget):
    log_requested = Signal(str, str, str)
    status_requested = Signal(str, int)

    def __init__(
        self,
        viewmodel: TaskViewModel | None = None,
        record_manager: RecordManager | None = None,
        task_persistence: TaskPersistenceService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.viewmodel = viewmodel or TaskViewModel.with_demo_data()
        self.record_manager = record_manager
        self.task_persistence = task_persistence
        self.search_input = QLineEdit(self)
        self.table = QTableWidget(self)
        self.summary_label = QLabel(self)
        self._visible_tasks: list[RecordTask] = []
        self._action_column = 6
        self._start_selected_action: QAction | None = None
        self._stop_selected_action: QAction | None = None
        self._delete_selected_action: QAction | None = None
        self._edit_selected_action: QAction | None = None
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(1500)
        self._status_timer.timeout.connect(self._sync_runtime_statuses)
        self._build_ui()
        self.refresh_table()
        self._status_timer.start()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        toolbar = QToolBar("任务操作", self)
        toolbar.setMovable(False)
        layout.addWidget(toolbar)

        action_specs = (
            ("新增任务", self._add_task),
            ("编辑任务", self._edit_selected_task),
            ("启动选中", self._start_selected_task),
            ("停止选中", self._stop_selected_task),
            ("删除选中", self._delete_selected_task),
            ("导入任务", self._import_tasks),
            ("导出任务", self._export_tasks),
        )
        action_attrs = (
            None,
            "_edit_selected_action",
            "_start_selected_action",
            "_stop_selected_action",
            "_delete_selected_action",
            None,
            None,
        )
        for (text, handler), attr_name in zip(action_specs, action_attrs):
            action = QAction(text, self)
            action.triggered.connect(handler)
            toolbar.addAction(action)
            if attr_name is not None:
                setattr(self, attr_name, action)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("筛选", self))
        self.search_input.setPlaceholderText("按主播、平台、标题、链接或状态筛选")
        self.search_input.textChanged.connect(self.refresh_table)
        filter_row.addWidget(self.search_input, 1)

        refresh_button = QPushButton("刷新", self)
        refresh_button.clicked.connect(self.refresh_table)
        filter_row.addWidget(refresh_button)
        layout.addLayout(filter_row)

        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["任务 ID", "平台", "主播", "标题", "状态", "错误", "操作"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.itemSelectionChanged.connect(self._update_selection_actions)
        self.table.doubleClicked.connect(lambda *_: self._edit_selected_task())
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(self._action_column, QHeaderView.ResizeToContents)
        layout.addWidget(self.table, 1)

        self.summary_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.summary_label)
        self._update_selection_actions()

    def refresh_table(self, selected_task_id: str | None = None) -> None:
        target_task_id = selected_task_id if selected_task_id is not None else self._selected_task_id()
        tasks = self.viewmodel.visible_tasks(self.search_input.text())

        self._visible_tasks = tasks
        self.table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            self._set_row(row, task)

        self._restore_selection(target_task_id)
        self.summary_label.setText(self.viewmodel.summary_text(tasks))
        self._update_selection_actions()
        self._emit_log(f"已刷新任务列表，共 {len(tasks)} 个可见任务。", LEVEL_DEBUG)

    def _set_row(self, row: int, task: RecordTask) -> None:
        values = [
            task.task_id,
            self._platform_text(task),
            task.anchor_name or task.display_name or "-",
            task.title or "-",
            self._status_text(task),
            task.last_error or "-",
        ]
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self._apply_row_item_style(item, task)
            self.table.setItem(row, column, item)
        self.table.setCellWidget(row, 4, self._build_status_badge(task))
        self.table.setCellWidget(row, self._action_column, self._build_action_buttons(task))

    def _selected_task(self) -> RecordTask | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._visible_tasks):
            return None
        return self._visible_tasks[row]

    def _selected_task_id(self) -> str | None:
        task = self._selected_task()
        return task.task_id if task is not None else None

    def _restore_selection(self, task_id: str | None) -> None:
        if not task_id:
            self.table.clearSelection()
            return

        for row, task in enumerate(self._visible_tasks):
            if task.task_id == task_id:
                self.table.selectRow(row)
                self.table.setCurrentCell(row, 0)
                return
        self.table.clearSelection()

    def _add_task(self) -> None:
        self._open_task_editor()

    def _edit_selected_task(self) -> None:
        task = self._selected_task()
        if task is None:
            self._notify_no_selection("请先选择要编辑的任务。")
            return
        self._open_task_editor(task)

    def _delete_selected_task(self) -> None:
        task = self._selected_task()
        if task is None:
            self._notify_no_selection("请先选择要删除的任务。")
            return

        reply = QMessageBox.question(
            self,
            "删除任务",
            f"确认删除任务 {task.task_id} 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        result = self.viewmodel.delete_task(
            task.task_id,
            task_persistence=self.task_persistence,
            record_manager=self.record_manager,
        )
        self._apply_action_result(result)

    def _import_tasks(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入任务",
            "",
            "任务文件 (*.json *.ini *.txt);;JSON 文件 (*.json);;旧版配置 (*.ini *.txt);;所有文件 (*.*)",
        )
        if not file_path:
            return

        result = self.viewmodel.import_tasks(
            Path(file_path),
            task_persistence=self.task_persistence,
            record_manager=self.record_manager,
            default_quality=self.viewmodel.default_quality(self.record_manager),
        )
        self._apply_action_result(result)

    def _export_tasks(self) -> None:
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出任务",
            "tasks-export.json",
            "JSON 文件 (*.json);;旧版配置 (*.ini);;文本文件 (*.txt)",
        )
        if not file_path:
            return

        export_path = Path(file_path)
        if not export_path.suffix:
            export_path = export_path.with_suffix(".ini" if "*.ini" in selected_filter else ".json")

        result = self.viewmodel.export_tasks(export_path, task_persistence=self.task_persistence)
        self._apply_action_result(result)

    def _start_selected_task(self) -> None:
        task = self._selected_task()
        if task is None:
            self._notify_no_selection("请先选择要启动的任务。")
            return
        result = self.viewmodel.start_task(task.task_id, record_manager=self.record_manager)
        self._apply_action_result(result)

    def _stop_selected_task(self) -> None:
        task = self._selected_task()
        if task is None:
            self._notify_no_selection("请先选择要停止的任务。")
            return
        result = self.viewmodel.stop_task(task.task_id, record_manager=self.record_manager)
        self._apply_action_result(result)

    def _open_task_editor(self, task: RecordTask | None = None) -> None:
        if task is not None and self.viewmodel.is_task_active(task, self.record_manager):
            self.status_requested.emit("运行中的任务请先停止后再编辑。", 3000)
            return
        if self.task_persistence is None:
            self.status_requested.emit("当前未配置任务存储，无法保存任务。", 3000)
            return

        dialog = TaskEditorDialog(
            platform_router=self._platform_router(),
            parent=self,
            task=task,
            default_quality=self.viewmodel.default_quality(self.record_manager),
        )
        if dialog.exec() != QDialog.Accepted:
            return

        result = self.viewmodel.save_task(
            dialog.payload(),
            task_persistence=self.task_persistence,
            record_manager=self.record_manager,
            task_id=task.task_id if task is not None else None,
        )
        self._apply_action_result(result)

    def _apply_action_result(self, result: TaskActionResult) -> None:
        self._emit_log(result.message, result.level)
        if result.status_message:
            self.status_requested.emit(result.status_message, result.status_timeout)
        if result.dialog_title and result.dialog_message:
            QMessageBox.warning(self, result.dialog_title, result.dialog_message)
        if result.refresh:
            self.refresh_table(result.selected_task_id)

    def _platform_router(self):
        assert self.task_persistence is not None
        return self.task_persistence.platform_router

    def _notify_no_selection(self, message: str) -> None:
        self._emit_log(message, LEVEL_WARNING)
        self.status_requested.emit(message, 2500)

    def _build_action_buttons(self, task: RecordTask) -> QWidget:
        container = QWidget(self.table)
        container.setStyleSheet(self._build_row_container_style(task))
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        start_button = QPushButton("启动", container)
        start_button.setFixedHeight(24)
        start_button.clicked.connect(lambda checked=False, current=task: self._apply_action_result(self.viewmodel.start_task(current.task_id, record_manager=self.record_manager)))
        layout.addWidget(start_button)

        stop_button = QPushButton("停止", container)
        stop_button.setFixedHeight(24)
        stop_button.clicked.connect(lambda checked=False, current=task: self._apply_action_result(self.viewmodel.stop_task(current.task_id, record_manager=self.record_manager)))
        layout.addWidget(stop_button)

        edit_button = QPushButton("编辑", container)
        edit_button.setFixedHeight(24)
        edit_button.clicked.connect(lambda checked=False, current=task: self._open_task_editor(current))
        layout.addWidget(edit_button)

        delete_button = QPushButton("删除", container)
        delete_button.setFixedHeight(24)
        delete_button.clicked.connect(lambda checked=False, current=task: self._delete_task_from_button(current))
        layout.addWidget(delete_button)

        is_active = self.viewmodel.is_task_active(task, self.record_manager)
        start_button.setEnabled(not is_active)
        stop_button.setEnabled(is_active)
        edit_button.setEnabled(not is_active)
        return container

    def _delete_task_from_button(self, task: RecordTask) -> None:
        self.table.clearSelection()
        result = QMessageBox.question(
            self,
            "删除任务",
            f"确认删除任务 {task.task_id} 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result != QMessageBox.Yes:
            return
        action_result = self.viewmodel.delete_task(
            task.task_id,
            task_persistence=self.task_persistence,
            record_manager=self.record_manager,
        )
        self._apply_action_result(action_result)

    def _build_status_badge(self, task: RecordTask) -> QWidget:
        container = QWidget(self.table)
        container.setStyleSheet(self._build_row_container_style(task))
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setAlignment(Qt.AlignCenter)

        background, foreground = STATUS_BADGE_STYLES.get(task.status, STATUS_BADGE_STYLES[TaskStatus.IDLE])
        badge = QLabel(self._status_text(task), container)
        badge.setAlignment(Qt.AlignCenter)
        badge.setMinimumWidth(72)
        badge.setStyleSheet(
            "QLabel {"
            f"background-color: {background};"
            f"color: {foreground};"
            "border-radius: 10px;"
            "font-weight: 600;"
            "padding: 4px 10px;"
            "}"
        )
        layout.addWidget(badge)
        return container

    def _show_context_menu(self, pos) -> None:
        index = self.table.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        if row < 0 or row >= len(self._visible_tasks):
            return

        task = self._visible_tasks[row]
        self.table.selectRow(row)
        is_active = self.viewmodel.is_task_active(task, self.record_manager)

        menu = QMenu(self)
        start_action = menu.addAction("启动任务")
        stop_action = menu.addAction("停止任务")
        edit_action = menu.addAction("编辑任务")
        menu.addSeparator()
        delete_action = menu.addAction("删除任务")
        start_action.setEnabled(not is_active)
        stop_action.setEnabled(is_active)
        edit_action.setEnabled(not is_active)

        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen is start_action:
            self._apply_action_result(self.viewmodel.start_task(task.task_id, record_manager=self.record_manager))
        elif chosen is stop_action:
            self._apply_action_result(self.viewmodel.stop_task(task.task_id, record_manager=self.record_manager))
        elif chosen is edit_action:
            self._open_task_editor(task)
        elif chosen is delete_action:
            self._delete_task_from_button(task)

    def _update_selection_actions(self) -> None:
        task = self._selected_task()
        has_task = task is not None
        is_active = self.viewmodel.is_task_active(task, self.record_manager) if task is not None else False

        if self._start_selected_action is not None:
            self._start_selected_action.setEnabled(has_task and not is_active)
        if self._stop_selected_action is not None:
            self._stop_selected_action.setEnabled(has_task and is_active)
        if self._edit_selected_action is not None:
            self._edit_selected_action.setEnabled(has_task and not is_active)
        if self._delete_selected_action is not None:
            self._delete_selected_action.setEnabled(has_task)

    def _sync_runtime_statuses(self) -> None:
        if self.record_manager is None:
            return
        if self.record_manager.sync_task_states():
            self.refresh_table()

    def _apply_row_item_style(self, item: QTableWidgetItem, task: RecordTask) -> None:
        row_color = ROW_HIGHLIGHT_COLORS.get(task.status)
        if row_color is not None:
            item.setBackground(row_color)

    def _build_row_container_style(self, task: RecordTask) -> str:
        row_color = ROW_HIGHLIGHT_COLORS.get(task.status)
        if row_color is None:
            return "background: transparent;"
        return f"background-color: {row_color.name()};"

    def _status_text(self, task: RecordTask) -> str:
        return STATUS_LABELS.get(task.status, task.status.value)

    def _platform_text(self, task: RecordTask) -> str:
        return PLATFORM_LABELS.get(task.platform, task.platform.value)

    def _emit_log(self, message: str, level: str) -> None:
        self.log_requested.emit(message, level, SOURCE_TASKS)
