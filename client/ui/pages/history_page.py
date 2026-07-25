"""History page UI."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from client.core.enums import Platform, TaskStatus
from client.core.history_service import HistoryService
from client.core.models import HistoryRecord
from client.infra.logging.log_service import LEVEL_INFO, SOURCE_HISTORY

STATUS_LABELS: dict[TaskStatus, str] = {
    TaskStatus.RUNNING: "运行中",
    TaskStatus.STOPPED: "已停止",
    TaskStatus.COMPLETED: "已完成",
    TaskStatus.FAILED: "失败",
    TaskStatus.IDLE: "空闲",
    TaskStatus.PENDING: "准备中",
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

STATUS_COLORS: dict[TaskStatus, QColor] = {
    TaskStatus.RUNNING: QColor("#ECFDF3"),
    TaskStatus.COMPLETED: QColor("#EFF6FF"),
    TaskStatus.STOPPED: QColor("#F8FAFC"),
    TaskStatus.FAILED: QColor("#FEF2F2"),
}


class HistoryPage(QWidget):
    log_requested = Signal(str, str, str)
    status_requested = Signal(str, int)

    def __init__(self, history_service: HistoryService | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.history_service = history_service
        self.search_input = QLineEdit(self)
        self.table = QTableWidget(self)
        self.summary_label = QLabel(self)
        self._records: list[HistoryRecord] = []
        self._build_ui()
        if self.history_service is not None:
            self.history_service.register_listener(self.refresh_table)
        self.refresh_table()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        toolbar = QToolBar("历史操作", self)
        toolbar.setMovable(False)
        layout.addWidget(toolbar)

        refresh_action = QAction("刷新历史", self)
        refresh_action.triggered.connect(self.refresh_table)
        toolbar.addAction(refresh_action)

        export_action = QAction("导出历史", self)
        export_action.triggered.connect(self.export_history)
        toolbar.addAction(export_action)

        clear_action = QAction("清空历史", self)
        clear_action.triggered.connect(self.clear_history)
        toolbar.addAction(clear_action)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("筛选", self))
        self.search_input.setPlaceholderText("按任务 ID、主播、标题、状态或文件路径筛选")
        self.search_input.textChanged.connect(self.refresh_table)
        filter_row.addWidget(self.search_input, 1)
        refresh_button = QPushButton("刷新", self)
        refresh_button.clicked.connect(self.refresh_table)
        filter_row.addWidget(refresh_button)
        layout.addLayout(filter_row)

        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["任务 ID", "平台", "主播", "标题", "结果", "开始时间", "结束时间", "时长", "输出文件"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        layout.addWidget(self.table, 1)

        self.summary_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.summary_label)

    def refresh_table(self) -> None:
        records = self.history_service.list_all() if self.history_service is not None else []
        keyword = self.search_input.text().strip().lower()
        if keyword:
            records = [
                record
                for record in records
                if keyword in record.task_id.lower()
                or keyword in record.display_name.lower()
                or keyword in record.title.lower()
                or keyword in self._status_text(record.status).lower()
                or keyword in str(record.file_path or "").lower()
            ]

        self._records = records
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            self._set_row(row, record)

        completed_count = sum(1 for record in self._records if record.status == TaskStatus.COMPLETED)
        failed_count = sum(1 for record in self._records if record.status == TaskStatus.FAILED)
        self.summary_label.setText(f"共 {len(records)} 条历史记录，已完成 {completed_count} 条，失败 {failed_count} 条")

    def export_history(self) -> None:
        default_name = f"history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出历史记录",
            str(Path(default_name)),
            "CSV 文件 (*.csv);;所有文件 (*)",
        )
        if not file_path:
            return

        lines = ["任务ID,平台,主播,标题,结果,开始时间,结束时间,时长,输出文件,错误信息"]
        for record in self._records:
            lines.append(
                ",".join(
                    [
                        self._csv_value(record.task_id),
                        self._csv_value(self._platform_text(record.platform)),
                        self._csv_value(record.display_name),
                        self._csv_value(record.title),
                        self._csv_value(self._status_text(record.status)),
                        self._csv_value(self._datetime_text(record.started_at)),
                        self._csv_value(self._datetime_text(record.finished_at)),
                        self._csv_value(self._duration_text(record)),
                        self._csv_value(str(record.file_path or "")),
                        self._csv_value(record.error_message),
                    ]
                )
            )
        Path(file_path).write_text("\n".join(lines), encoding="utf-8")
        self._emit_log(f"已导出历史记录到 {file_path}", LEVEL_INFO)
        self.status_requested.emit(f"已导出历史记录到 {file_path}", 3000)

    def clear_history(self) -> None:
        if self.history_service is None:
            self.status_requested.emit("当前未连接历史服务。", 2500)
            return
        reply = QMessageBox.question(
            self,
            "清空历史",
            "确认清空所有历史记录吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.history_service.clear()
        self._emit_log("已清空历史记录。", LEVEL_INFO)
        self.status_requested.emit("已清空历史记录。", 2500)

    def _set_row(self, row: int, record: HistoryRecord) -> None:
        values = [
            record.task_id,
            self._platform_text(record.platform),
            record.display_name or "-",
            record.title or "-",
            self._status_text(record.status),
            self._datetime_text(record.started_at),
            self._datetime_text(record.finished_at),
            self._duration_text(record),
            str(record.file_path or "-"),
        ]
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            color = STATUS_COLORS.get(record.status)
            if color is not None:
                item.setBackground(color)
            self.table.setItem(row, column, item)
        if record.error_message:
            self.table.item(row, 4).setToolTip(record.error_message)
            self.table.item(row, 8).setToolTip(record.error_message)

    def _duration_text(self, record: HistoryRecord) -> str:
        if record.started_at is None:
            return "-"
        end_time = record.finished_at or datetime.now()
        seconds = max(int((end_time - record.started_at).total_seconds()), 0)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _datetime_text(self, value: datetime | None) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S") if value is not None else "-"

    def _status_text(self, status: TaskStatus) -> str:
        return STATUS_LABELS.get(status, status.value)

    def _platform_text(self, platform: Platform) -> str:
        return PLATFORM_LABELS.get(platform, platform.value)

    def _csv_value(self, value: str) -> str:
        escaped = value.replace('"', '""')
        return f'"{escaped}"'

    def _emit_log(self, message: str, level: str) -> None:
        self.log_requested.emit(message, level, SOURCE_HISTORY)
