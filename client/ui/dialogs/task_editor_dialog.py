"""Task editor dialog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from client.core.enums import Platform
from client.core.models import RecordTask
from client.core.platform_router import PlatformRouter

QUALITY_OPTIONS = ["\u539f\u753b", "\u8d85\u6e05", "\u9ad8\u6e05", "\u6807\u6e05", "\u6d41\u7545"]
PLATFORM_LABELS: dict[Platform, str] = {
    Platform.UNKNOWN: "\u672a\u77e5",
    Platform.DIRECT: "\u76f4\u94fe",
    Platform.DOUYIN: "\u6296\u97f3",
    Platform.TIKTOK: "TikTok",
    Platform.KUAISHOU: "\u5feb\u624b",
    Platform.HUYA: "\u864e\u7259",
    Platform.DOUYU: "\u6597\u9c7c",
    Platform.YY: "YY",
    Platform.BILIBILI: "Bilibili",
    Platform.NETEASE_CC: "\u7f51\u6613CC",
    Platform.QIANDUREBO: "\u5343\u5ea6\u70ed\u64ad",
    Platform.PANDATV: "PandaTV",
    Platform.BAIDU: "\u767e\u5ea6\u76f4\u64ad",
    Platform.SHOWROOM: "ShowRoom",
    Platform.CHZZK: "CHZZK",
}


class TaskEditorDialog(QDialog):
    def __init__(
        self,
        *,
        platform_router: PlatformRouter,
        parent: QWidget | None = None,
        task: RecordTask | None = None,
        default_quality: str = "\u539f\u753b",
    ) -> None:
        super().__init__(parent)
        self.platform_router = platform_router
        self.task = task
        self.url_input = QLineEdit(self)
        self.display_name_input = QLineEdit(self)
        self.quality_combo = QComboBox(self)
        self.enabled_checkbox = QCheckBox("\u542f\u7528\u8be5\u4efb\u52a1", self)
        self.platform_value_label = QLabel(self)
        self.task_id_value_label = QLabel(self)
        self._default_quality = default_quality or "\u539f\u753b"
        self._build_ui()
        self._load_task()

    def _build_ui(self) -> None:
        self.setWindowTitle("\u65b0\u589e\u4efb\u52a1" if self.task is None else "\u7f16\u8f91\u4efb\u52a1")
        self.setModal(True)
        self.resize(560, 260)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.quality_combo.addItems(QUALITY_OPTIONS)
        self.display_name_input.setPlaceholderText("\u4f8b\u5982\uff1a\u4e3b\u64ad\u5907\u6ce8\u6216\u81ea\u5b9a\u4e49\u540d\u79f0")
        self.url_input.setPlaceholderText("\u8bf7\u8f93\u5165\u76f4\u64ad\u95f4\u94fe\u63a5")
        self.url_input.textChanged.connect(self._update_platform_preview)

        form.addRow("\u4efb\u52a1 ID", self.task_id_value_label)
        form.addRow("\u76f4\u64ad\u94fe\u63a5", self.url_input)
        form.addRow("\u663e\u793a\u540d\u79f0", self.display_name_input)
        form.addRow("\u5f55\u5236\u753b\u8d28", self.quality_combo)
        form.addRow("\u5e73\u53f0\u8bc6\u522b", self.platform_value_label)
        form.addRow("", self.enabled_checkbox)
        layout.addLayout(form)

        hint_layout = QHBoxLayout()
        hint_label = QLabel("\u63d0\u793a\uff1a\u5982\u672a\u586b\u663e\u793a\u540d\u79f0\uff0c\u4efb\u52a1\u5217\u8868\u4f1a\u5728\u5f55\u5236\u540e\u4f18\u5148\u663e\u793a\u4e3b\u64ad\u540d\u3002", self)
        hint_label.setWordWrap(True)
        hint_layout.addWidget(hint_label)
        layout.addLayout(hint_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_task(self) -> None:
        if self.task is None:
            self.task_id_value_label.setText("\u81ea\u52a8\u751f\u6210")
            self.quality_combo.setCurrentText(self._default_quality)
            self.enabled_checkbox.setChecked(True)
        else:
            self.task_id_value_label.setText(self.task.task_id)
            self.url_input.setText(self.task.url)
            self.display_name_input.setText(self.task.display_name)
            self.quality_combo.setCurrentText(self.task.quality or self._default_quality)
            self.enabled_checkbox.setChecked(self.task.enabled)
        self._update_platform_preview()

    def _update_platform_preview(self) -> None:
        platform = self.platform_router.detect_platform(self.url_input.text().strip())
        self.platform_value_label.setText(PLATFORM_LABELS.get(platform, platform.value))

    def payload(self) -> dict[str, str | bool]:
        return {
            "url": self.url_input.text().strip(),
            "display_name": self.display_name_input.text().strip(),
            "quality": self.quality_combo.currentText().strip() or self._default_quality,
            "enabled": self.enabled_checkbox.isChecked(),
        }

    def _submit(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "\u7f3a\u5c11\u5185\u5bb9", "\u8bf7\u5148\u8f93\u5165\u76f4\u64ad\u94fe\u63a5\u3002")
            self.url_input.setFocus()
            return
        self.accept()
