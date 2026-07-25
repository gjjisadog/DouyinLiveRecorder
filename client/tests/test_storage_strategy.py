from __future__ import annotations

import json
import os
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from client.app_settings import AppSettings
from client.bootstrap import _initialize_storage_strategy
from client.infra.storage.sqlite_repo import SqliteRepository
from client.infra.storage.storage_strategy import PRIMARY_STORAGE_MODE, STORAGE_STRATEGY_VERSION, StorageStrategyService


class StorageStrategyTests(unittest.TestCase):
    def make_workspace(self, prefix: str) -> Path:
        root = Path.cwd() / f"{prefix}_{uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def test_storage_strategy_service_writes_manifest_and_initializes_sqlite_foundation(self) -> None:
        root = self.make_workspace("tmp_storage_strategy")
        data_dir = root / "client_data"
        manifest_path = data_dir / "storage_meta.json"
        database_path = data_dir / "client.db"
        service = StorageStrategyService(manifest_path=manifest_path, database_path=database_path)

        manifest = service.ensure_initialized()

        self.assertEqual(PRIMARY_STORAGE_MODE, manifest["mode"])
        self.assertTrue(manifest["sqlite_foundation"]["ready"])
        self.assertEqual(STORAGE_STRATEGY_VERSION, manifest["sqlite_foundation"]["schema_version"])
        self.assertTrue(manifest_path.exists())
        self.assertTrue(database_path.exists())
        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(PRIMARY_STORAGE_MODE, saved["mode"])
        self.assertEqual(["config", "tasks", "history", "sqlite_foundation"], [item["name"] for item in saved["boundaries"]])

    def test_sqlite_repository_reports_schema_version_and_metadata(self) -> None:
        root = self.make_workspace("tmp_sqlite_repo")
        repo = SqliteRepository(root / "client_data" / "client.db")

        repo.initialize(schema_version=3)

        self.assertEqual(3, repo.get_schema_version())
        metadata = repo.get_metadata()
        self.assertEqual("3", metadata["schema_version"])
        self.assertIn("initialized_at", metadata)
        self.assertIn("last_initialized_at", metadata)

    def test_bootstrap_storage_initialization_uses_app_settings_paths(self) -> None:
        root = self.make_workspace("tmp_storage_bootstrap")
        settings = AppSettings(data_dir=root / "client_data")
        logs: list[tuple[str, str | None, str | None]] = []

        manifest = _initialize_storage_strategy(
            settings,
            log_handler=lambda message, level=None, source=None: logs.append((message, level, source)),
        )

        self.assertEqual(PRIMARY_STORAGE_MODE, manifest["mode"])
        self.assertTrue(settings.storage_meta_path.exists())
        self.assertTrue(settings.database_path.exists())
        self.assertTrue(any("存储策略已确认" in message for message, _, _ in logs))


if __name__ == "__main__":
    unittest.main()
