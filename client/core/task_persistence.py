"""Task persistence for the desktop client."""

from __future__ import annotations

import json
import re
from pathlib import Path

from client.core.enums import Platform, TaskStatus
from client.core.models import RecordTask
from client.core.platform_router import PlatformRouter
from client.infra.logging.log_service import LEVEL_DEBUG, LEVEL_INFO, LEVEL_WARNING, LogEmitterMixin, LogHandler, SOURCE_TASK_STORE
from client.infra.storage.json_store import JsonStore

TASK_ID_PATTERN = re.compile(r"task-(\d+)$")
DEFAULT_QUALITY = "原画"
TEXT_ENCODING = "utf-8-sig"
QUALITY_NAMES = {
    "原画",
    "蓝光",
    "超清",
    "高清",
    "标清",
    "流畅",
}


class TaskPersistenceService(LogEmitterMixin):
    def __init__(
        self,
        file_path: Path,
        platform_router: PlatformRouter | None = None,
        log_handler: LogHandler | None = None,
    ) -> None:
        super().__init__(log_handler=log_handler, log_source=SOURCE_TASK_STORE)
        self.file_path = file_path
        self.store = JsonStore(file_path)
        self.platform_router = platform_router or PlatformRouter()

    def load_tasks(self, seed_tasks: list[RecordTask] | None = None) -> list[RecordTask]:
        self._emit_log(f"开始加载任务存储：{self.file_path}", LEVEL_DEBUG)
        payload = self.store.load(on_error=self._handle_store_error)
        if isinstance(payload, dict) and isinstance(payload.get("tasks"), list):
            tasks = self._deserialize_tasks(payload["tasks"])
            self._emit_log(f"已从本地任务存储加载 {len(tasks)} 个任务。", LEVEL_INFO)
            return tasks

        tasks = [self._clone_task(task) for task in (seed_tasks or [])]
        self.save_tasks(tasks)
        self._emit_log(f"本地任务存储为空，已使用种子任务初始化 {len(tasks)} 个任务。", LEVEL_INFO)
        return tasks

    def save_tasks(self, tasks: list[RecordTask]) -> None:
        payload = {
            "version": 1,
            "tasks": [self._serialize_task(task) for task in tasks],
        }
        self.store.save(payload)
        self._emit_log(f"已保存 {len(tasks)} 个任务到本地任务存储。", LEVEL_INFO)

    def load_tasks_from_file(self, file_path: Path, default_quality: str = DEFAULT_QUALITY) -> list[RecordTask]:
        import_path = Path(file_path)
        if not import_path.exists():
            raise FileNotFoundError(import_path)

        if import_path.suffix.lower() == ".json":
            tasks = self._deserialize_tasks(self._load_json_items(import_path))
            self._emit_log(f"已从 {import_path.name} 导入 {len(tasks)} 个 JSON 任务。", LEVEL_INFO)
            return tasks

        tasks = self._load_legacy_tasks(import_path, default_quality)
        self._emit_log(f"已从 {import_path.name} 导入 {len(tasks)} 个旧版任务。", LEVEL_INFO)
        return tasks

    def export_tasks_to_file(self, tasks: list[RecordTask], file_path: Path) -> None:
        export_path = Path(file_path)
        export_path.parent.mkdir(parents=True, exist_ok=True)

        if export_path.suffix.lower() == ".json":
            payload = {
                "version": 1,
                "tasks": [self._serialize_task(task) for task in tasks],
            }
            export_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self._emit_log(f"已导出 {len(tasks)} 个任务到 JSON 文件：{export_path}", LEVEL_INFO)
            return

        lines = [self._serialize_legacy_task(task) for task in tasks]
        content = "\n".join(lines)
        if lines:
            content += "\n"
        export_path.write_text(content, encoding=TEXT_ENCODING)
        self._emit_log(f"已导出 {len(tasks)} 个任务到旧版格式文件：{export_path}", LEVEL_INFO)

    def merge_imported_tasks(
        self,
        existing: list[RecordTask],
        imported: list[RecordTask],
        active_task_ids: set[str] | None = None,
    ) -> tuple[list[RecordTask], int, int, int]:
        merged = list(existing)
        existing_by_url = {self.normalize_url(task.url): task for task in merged}
        seen_import_urls: set[str] = set()
        active_ids = active_task_ids or set()
        added = 0
        updated = 0
        skipped = 0

        for imported_task in imported:
            normalized_url = self.normalize_url(imported_task.url)
            if not normalized_url:
                skipped += 1
                continue
            if normalized_url in seen_import_urls:
                skipped += 1
                continue
            seen_import_urls.add(normalized_url)

            existing_task = existing_by_url.get(normalized_url)
            if existing_task is not None:
                if existing_task.task_id in active_ids:
                    skipped += 1
                    continue
                self.update_task(
                    existing_task,
                    url=normalized_url,
                    quality=imported_task.quality,
                    display_name=imported_task.display_name,
                    enabled=imported_task.enabled,
                )
                updated += 1
                continue

            new_task = self.create_task(
                tasks=merged,
                url=normalized_url,
                quality=imported_task.quality,
                display_name=imported_task.display_name,
                enabled=imported_task.enabled,
            )
            merged.append(new_task)
            existing_by_url[normalized_url] = new_task
            added += 1

        self._emit_log(f"任务导入合并完成：新增 {added}，更新 {updated}，跳过 {skipped}。", LEVEL_INFO)
        return merged, added, updated, skipped

    def create_task(
        self,
        *,
        tasks: list[RecordTask],
        url: str,
        quality: str,
        display_name: str,
        enabled: bool,
    ) -> RecordTask:
        normalized_url = self.normalize_url(url)
        task = RecordTask(
            task_id=self.next_task_id(tasks),
            url=normalized_url,
            platform=self.platform_router.detect_platform(normalized_url),
            quality=quality or DEFAULT_QUALITY,
            enabled=enabled,
            display_name=display_name.strip(),
        )
        self._emit_log(f"已生成新任务草稿 {task.task_id}。", LEVEL_DEBUG)
        return task

    def update_task(
        self,
        task: RecordTask,
        *,
        url: str,
        quality: str,
        display_name: str,
        enabled: bool,
    ) -> None:
        normalized_url = self.normalize_url(url)
        task.url = normalized_url
        task.platform = self.platform_router.detect_platform(normalized_url)
        task.quality = quality or DEFAULT_QUALITY
        task.enabled = enabled
        task.display_name = display_name.strip()
        self._emit_log(f"已更新任务 {task.task_id} 的本地存储字段。", LEVEL_DEBUG)

    def normalize_url(self, url: str) -> str:
        normalized = url.strip()
        if normalized and "://" not in normalized:
            normalized = f"https://{normalized}"
        return normalized

    def next_task_id(self, tasks: list[RecordTask]) -> str:
        highest = 0
        for task in tasks:
            match = TASK_ID_PATTERN.fullmatch(task.task_id)
            if match:
                highest = max(highest, int(match.group(1)))
        return f"task-{highest + 1:03d}"

    def _load_json_items(self, file_path: Path) -> list[dict]:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("tasks"), list):
            return [item for item in payload["tasks"] if isinstance(item, dict)]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        raise ValueError(f"Invalid task JSON structure: {file_path}")

    def _load_legacy_tasks(self, file_path: Path, default_quality: str) -> list[RecordTask]:
        tasks: list[RecordTask] = []
        lines = file_path.read_text(encoding=TEXT_ENCODING, errors="ignore").splitlines()
        for line_number, raw_line in enumerate(lines, start=1):
            task = self._parse_legacy_line(raw_line, line_number=line_number, default_quality=default_quality)
            if task is not None:
                tasks.append(task)
        return tasks

    def _parse_legacy_line(self, raw_line: str, *, line_number: int, default_quality: str) -> RecordTask | None:
        original = raw_line.strip()
        if not original:
            return None

        enabled = not original.startswith("#")
        line = original.lstrip("#").strip()
        if len(line) < 5:
            return None

        parts = [part.strip() for part in re.split(r"[,，]", line) if part.strip()]
        quality = default_quality
        url = ""
        display_name = ""

        if len(parts) == 1:
            url = parts[0]
        elif len(parts) == 2:
            if self._contains_url(parts[0]):
                url, display_name = parts
            else:
                quality, url = parts
        else:
            quality, url, display_name = parts[0], parts[1], parts[2]

        if quality not in QUALITY_NAMES:
            quality = default_quality

        normalized_url = self.normalize_url(url)
        if not normalized_url:
            return None

        return RecordTask(
            task_id=f"task-{line_number:03d}",
            url=normalized_url,
            platform=self.platform_router.detect_platform(normalized_url),
            quality=quality,
            enabled=enabled,
            display_name=display_name,
        )

    def _deserialize_tasks(self, items: list[dict]) -> list[RecordTask]:
        tasks: list[RecordTask] = []
        for index, item in enumerate(items, start=1):
            task_id = str(item.get("task_id") or f"task-{index:03d}")
            url = self.normalize_url(str(item.get("url") or ""))
            if not url:
                continue
            quality = str(item.get("quality") or DEFAULT_QUALITY)
            display_name = str(item.get("display_name") or "")
            enabled = bool(item.get("enabled", True))
            platform = self._parse_platform(str(item.get("platform") or ""), url)
            tasks.append(
                RecordTask(
                    task_id=task_id,
                    url=url,
                    platform=platform,
                    quality=quality,
                    enabled=enabled,
                    display_name=display_name,
                    anchor_name=str(item.get("anchor_name") or ""),
                    title=str(item.get("title") or ""),
                    status=TaskStatus.IDLE,
                    output_path=None,
                    last_error="",
                )
            )
        return tasks

    def _serialize_task(self, task: RecordTask) -> dict[str, str | bool]:
        return {
            "task_id": task.task_id,
            "url": task.url,
            "platform": task.platform.value,
            "quality": task.quality,
            "enabled": task.enabled,
            "display_name": task.display_name,
            "anchor_name": task.anchor_name,
            "title": task.title,
        }

    def _serialize_legacy_task(self, task: RecordTask) -> str:
        parts = [task.quality or DEFAULT_QUALITY, self.normalize_url(task.url)]
        if task.display_name.strip():
            parts.append(task.display_name.strip())
        line = ",".join(parts)
        if not task.enabled:
            return f"#{line}"
        return line

    def _parse_platform(self, raw_platform: str, url: str) -> Platform:
        try:
            return Platform(raw_platform)
        except ValueError:
            return self.platform_router.detect_platform(url)

    def _clone_task(self, task: RecordTask) -> RecordTask:
        return RecordTask(
            task_id=task.task_id,
            url=task.url,
            platform=task.platform,
            quality=task.quality,
            enabled=task.enabled,
            display_name=task.display_name,
            anchor_name=task.anchor_name,
            title=task.title,
            status=TaskStatus.IDLE,
            output_path=None,
            last_error="",
        )

    def _contains_url(self, value: str) -> bool:
        pattern = r"(https?://)?(www\.)?[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+(:\d+)?(/.*)?"
        return re.search(pattern, value) is not None

    def _handle_store_error(self, exc: Exception, path: Path, backup_path: Path | None) -> None:
        suffix = f"，已备份到 {backup_path}" if backup_path is not None else ""
        self._emit_log(f"读取任务存储失败：{path}，将回退到种子任务。{exc}{suffix}", LEVEL_WARNING)
