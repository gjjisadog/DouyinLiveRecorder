"""Logs page UI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QDateTime, Qt, Signal
from PySide6.QtGui import QAction, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSizePolicy,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from client.infra.logging.log_service import (
    KNOWN_SOURCES,
    LEVEL_ALL,
    SOURCE_ALL,
    LogService,
)


@dataclass(slots=True)
class LogEntry:
    timestamp: str
    level: str
    source: str
    message: str

    @property
    def display_text(self) -> str:
        level_text = LogService.level_label(self.level)
        source_text = LogService.source_label(self.source)
        return f"[{self.timestamp}] [{level_text}] [{source_text}] {self.message}"


class ElidedLabel(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_text = ""
        self.setText(text)

    def setText(self, text: str) -> None:
        self._full_text = text
        self.setToolTip(text if text else "")
        self._update_elided_text()

    def full_text(self) -> str:
        return self._full_text

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._update_elided_text()

    def _update_elided_text(self) -> None:
        metrics = self.fontMetrics()
        available_width = max(self.contentsRect().width(), 0)
        if available_width <= 0:
            super().setText(self._full_text)
            return
        super().setText(metrics.elidedText(self._full_text, Qt.ElideRight, available_width))


class LogsPage(QWidget):
    status_requested = Signal(str, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.editor = QPlainTextEdit(self)
        self.search_input = QLineEdit(self)
        self.level_filter = QComboBox(self)
        self.source_filter = QComboBox(self)
        self.summary_label = ElidedLabel(parent=self)
        self.stats_label = ElidedLabel(parent=self)
        self.auto_scroll_checkbox = QCheckBox("自动滚动到最新日志", self)
        self._entries: list[LogEntry] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        toolbar = QToolBar("日志操作", self)
        toolbar.setMovable(False)

        clear_action = QAction("清空日志", self)
        clear_action.triggered.connect(self.clear_logs)
        toolbar.addAction(clear_action)

        copy_action = QAction("复制当前结果", self)
        copy_action.triggered.connect(self.copy_visible_logs)
        toolbar.addAction(copy_action)

        export_action = QAction("导出日志", self)
        export_action.triggered.connect(self.export_logs)
        toolbar.addAction(export_action)

        reset_filters_action = QAction("清空筛选", self)
        reset_filters_action.triggered.connect(self.clear_filters)
        toolbar.addAction(reset_filters_action)

        layout.addWidget(toolbar)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("级别", self))
        for level in (LEVEL_ALL, *("info", "warning", "error", "debug")):
            self.level_filter.addItem(LogService.level_label(level), level)
        self.level_filter.currentIndexChanged.connect(self._refresh_view)
        filter_row.addWidget(self.level_filter)

        filter_row.addWidget(QLabel("来源", self))
        self.source_filter.addItem(LogService.source_label(SOURCE_ALL), SOURCE_ALL)
        for source in KNOWN_SOURCES:
            self.source_filter.addItem(LogService.source_label(source), source)
        self.source_filter.currentIndexChanged.connect(self._refresh_view)
        filter_row.addWidget(self.source_filter)

        filter_row.addWidget(QLabel("搜索", self))
        self.search_input.setPlaceholderText("按关键字筛选日志内容")
        self.search_input.textChanged.connect(self._refresh_view)
        filter_row.addWidget(self.search_input, 1)

        self.auto_scroll_checkbox.setChecked(True)
        self.auto_scroll_checkbox.toggled.connect(self._handle_auto_scroll_toggled)
        filter_row.addWidget(self.auto_scroll_checkbox)
        layout.addLayout(filter_row)

        self.editor.setReadOnly(True)
        self.editor.setPlaceholderText("运行日志会显示在这里。")
        layout.addWidget(self.editor, 1)

        status_row = QHBoxLayout()
        self.summary_label.setText("当前无日志。")
        self.summary_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        status_row.addWidget(self.summary_label, 2)
        self.stats_label.setText("统计：暂无。")
        self.stats_label.setStyleSheet("color: #6B7280;")
        self.stats_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.stats_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        status_row.addWidget(self.stats_label, 3)
        layout.addLayout(status_row)

    def append_log(self, message: str, level: str | None = None, source: str | None = None) -> None:
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        payload = LogService.parse(message=message, level=level, source=source)
        self._entries.append(
            LogEntry(
                timestamp=timestamp,
                level=payload.level,
                source=payload.source,
                message=payload.message,
            )
        )
        self._refresh_view()

    def clear_logs(self) -> None:
        self._entries.clear()
        self.editor.clear()
        self.summary_label.setText("当前无日志。")
        self.stats_label.setText("统计：暂无。")
        self.status_requested.emit("日志已清空。", 2500)

    def clear_filters(self) -> None:
        self.level_filter.setCurrentIndex(self.level_filter.findData(LEVEL_ALL))
        self.source_filter.setCurrentIndex(self.source_filter.findData(SOURCE_ALL))
        self.search_input.clear()
        self._refresh_view()
        self.status_requested.emit("日志筛选条件已清空。", 2500)

    def copy_visible_logs(self) -> None:
        visible_text = self._visible_text()
        QApplication.clipboard().setText(visible_text)
        self.status_requested.emit("当前日志已复制到剪贴板。", 2500)

    def export_logs(self) -> None:
        default_name = f"client_logs_{QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')}.log"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出日志",
            str(Path(default_name)),
            "日志文件 (*.log);;文本文件 (*.txt);;所有文件 (*)",
        )
        if not file_path:
            return

        Path(file_path).write_text(self._visible_text(), encoding="utf-8")
        self.status_requested.emit(f"日志已导出到 {file_path}", 3500)

    def _refresh_view(self) -> None:
        entries = self._filtered_entries()
        scroll_bar = self.editor.verticalScrollBar()
        previous_position = scroll_bar.value()
        self.editor.setPlainText("\n".join(entry.display_text for entry in entries))
        if self.auto_scroll_checkbox.isChecked():
            scroll_bar.setValue(scroll_bar.maximum())
        else:
            scroll_bar.setValue(min(previous_position, scroll_bar.maximum()))
        total_count = len(self._entries)
        visible_count = len(entries)
        if total_count == 0:
            self.summary_label.setText("当前无日志。")
            self.stats_label.setText("统计：暂无。")
            return
        source_count = len({entry.source for entry in self._entries})
        self.summary_label.setText(f"共 {total_count} 条日志，当前显示 {visible_count} 条，来源 {source_count} 个。")
        self.stats_label.setText(self._build_stats_text(entries))

    def _filtered_entries(self) -> list[LogEntry]:
        keyword = self.search_input.text().strip().lower()
        selected_level = self.level_filter.currentData()
        selected_source = self.source_filter.currentData()
        entries = self._entries
        if selected_level and selected_level != LEVEL_ALL:
            entries = [entry for entry in entries if entry.level == selected_level]
        if selected_source and selected_source != SOURCE_ALL:
            entries = [entry for entry in entries if entry.source == selected_source]
        if keyword:
            entries = [entry for entry in entries if keyword in entry.display_text.lower()]
        return entries

    def _visible_text(self) -> str:
        entries = self._filtered_entries()
        return "\n".join(entry.display_text for entry in entries)

    def _build_source_stats_text(self, entries: list[LogEntry]) -> str:
        if not entries:
            return "来源：当前筛选下无日志"

        counts: dict[str, int] = {}
        for entry in entries:
            counts[entry.source] = counts.get(entry.source, 0) + 1

        parts = [
            f"{LogService.source_label(source)} {count}"
            for source, count in sorted(
                counts.items(),
                key=lambda item: (-item[1], LogService.source_label(item[0])),
            )
        ]
        return "来源：" + " · ".join(parts)

    def _build_level_stats_text(self, entries: list[LogEntry]) -> str:
        if not entries:
            return "级别：当前筛选下无日志"

        counts: dict[str, int] = {}
        for entry in entries:
            counts[entry.level] = counts.get(entry.level, 0) + 1

        ordered_levels = ("error", "warning", "info", "debug")
        parts = [
            f"{LogService.level_label(level)} {counts[level]}"
            for level in ordered_levels
            if counts.get(level)
        ]
        return "级别：" + " · ".join(parts)

    def _build_stats_text(self, entries: list[LogEntry]) -> str:
        if not entries:
            return "统计：暂无。"
        return f"统计：{self._build_source_stats_text(entries)} ｜ {self._build_level_stats_text(entries)}"

    def _handle_auto_scroll_toggled(self, checked: bool) -> None:
        if checked:
            self._refresh_view()
            self.status_requested.emit("已开启自动滚动。", 2000)
            return
        self.status_requested.emit("已关闭自动滚动。", 2000)
