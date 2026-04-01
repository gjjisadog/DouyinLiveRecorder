"""Storage strategy and persisted backend metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from client.infra.logging.log_service import LEVEL_INFO, LEVEL_WARNING, LogEmitterMixin, LogHandler, SOURCE_SYSTEM
from client.infra.storage.json_store import JsonStore
from client.infra.storage.sqlite_repo import SqliteRepository

STORAGE_STRATEGY_VERSION = 1
PRIMARY_STORAGE_MODE = "json-primary-with-sqlite-foundation"


@dataclass(slots=True)
class StorageAreaPolicy:
    name: str
    backend: str
    file_name: str
    role: str
    migration_phase: str


class StorageStrategyService(LogEmitterMixin):
    def __init__(
        self,
        manifest_path: Path,
        database_path: Path,
        log_handler: LogHandler | None = None,
    ) -> None:
        super().__init__(log_handler=log_handler, log_source=SOURCE_SYSTEM)
        self.manifest_path = manifest_path
        self.database_path = database_path
        self.store = JsonStore(manifest_path)
        self.sqlite_repo = SqliteRepository(database_path)

    def ensure_initialized(self) -> dict:
        manifest = self.load()
        sqlite_ready = False
        sqlite_error = ""
        try:
            self.sqlite_repo.initialize(schema_version=STORAGE_STRATEGY_VERSION)
            sqlite_ready = True
            self._emit_log(f"已初始化 SQLite 迁移基座：{self.database_path}", LEVEL_INFO)
        except Exception as exc:
            sqlite_error = str(exc)
            self._emit_log(f"初始化 SQLite 迁移基座失败：{exc}", LEVEL_WARNING)

        desired = self._build_manifest(sqlite_ready=sqlite_ready, sqlite_error=sqlite_error)
        merged = self._merge_manifest(manifest, desired)
        self.store.save(merged)
        self._emit_log(f"已写入客户端存储策略清单：{self.manifest_path}", LEVEL_INFO)
        return merged

    def load(self) -> dict:
        payload = self.store.load(default={})
        if isinstance(payload, dict):
            return payload
        return {}

    def _build_manifest(self, *, sqlite_ready: bool, sqlite_error: str) -> dict:
        policies = [
            StorageAreaPolicy(
                name="config",
                backend="json",
                file_name="config.json",
                role="用户配置，体量小，便于手工检查与迁移",
                migration_phase="keep-json",
            ),
            StorageAreaPolicy(
                name="tasks",
                backend="json",
                file_name="tasks.json",
                role="录制任务集合，当前规模小，仍需兼容旧版 URL 配置导入导出",
                migration_phase="keep-json",
            ),
            StorageAreaPolicy(
                name="history",
                backend="json",
                file_name="history.json",
                role="历史记录按文件回写，当前查询维度简单，先保留 JSON",
                migration_phase="monitor-growth",
            ),
            StorageAreaPolicy(
                name="sqlite_foundation",
                backend="sqlite",
                file_name=self.database_path.name,
                role="为后续历史索引、检索和统计迁移预留基础设施",
                migration_phase="ready",
            ),
        ]
        return {
            "version": STORAGE_STRATEGY_VERSION,
            "mode": PRIMARY_STORAGE_MODE,
            "decision": {
                "summary": "当前客户端继续以 JSON 作为主存储，SQLite 仅作为已初始化的未来迁移基座。",
                "why": [
                    "config/tasks/history 目前数据量有限，JSON 易于排错、备份和兼容旧版配置。",
                    "现有核心链路已经围绕 JSON 建立容错与回退测试，直接切库风险高于收益。",
                    "历史记录和复杂查询未来更适合迁移到 SQLite，因此提前准备数据库文件与 schema 元信息。",
                ],
            },
            "boundaries": [self._serialize_policy(policy) for policy in policies],
            "sqlite_foundation": {
                "path": str(self.database_path),
                "ready": sqlite_ready,
                "schema_version": STORAGE_STRATEGY_VERSION if sqlite_ready else None,
                "last_error": sqlite_error,
            },
            "migration_plan": [
                "阶段 1：继续使用 config.json / tasks.json / history.json，保持现有兼容性与人工可恢复能力。",
                "阶段 2：若 history.json 增长到影响加载或筛选，再优先迁移历史索引与查询到 SQLite。",
                "阶段 3：在确认任务与配置编辑链路稳定后，再评估 tasks/config 是否需要合并进 SQLite。",
            ],
        }

    def _merge_manifest(self, existing: dict, desired: dict) -> dict:
        if not existing:
            return desired
        merged = dict(existing)
        merged.update(
            {
                "version": desired["version"],
                "mode": desired["mode"],
                "decision": desired["decision"],
                "boundaries": desired["boundaries"],
                "sqlite_foundation": desired["sqlite_foundation"],
                "migration_plan": desired["migration_plan"],
            }
        )
        return merged

    def _serialize_policy(self, policy: StorageAreaPolicy) -> dict[str, str]:
        return {
            "name": policy.name,
            "backend": policy.backend,
            "file_name": policy.file_name,
            "role": policy.role,
            "migration_phase": policy.migration_phase,
        }
