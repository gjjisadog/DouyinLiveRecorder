from __future__ import annotations

import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from client.infra.config_example_sync import (
    compare_ini_structure,
    validate_config_examples,
    validate_url_example,
)


class ConfigExampleSyncTests(unittest.TestCase):
    def make_workspace(self, prefix: str) -> Path:
        root = Path.cwd() / f"{prefix}_{uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def prepare_repo_root(self) -> Path:
        root = self.make_workspace("tmp_config_example_sync")
        config_dir = root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.ini").write_text(
            "[录制设置]\nfoo = 1\nbar = 2\n\n[推送配置]\nbaz = 3\n",
            encoding="utf-8",
        )
        (config_dir / "config.example.ini").write_text(
            "[录制设置]\nfoo = demo\nbar = demo\n\n[推送配置]\nbaz = demo\n",
            encoding="utf-8",
        )
        (config_dir / "URL_config.example.ini").write_text(
            "# 示例\n原画,https://live.douyin.com/123,示例主播\n",
            encoding="utf-8",
        )
        return root

    def test_compare_ini_structure_reports_missing_keys(self) -> None:
        repo_root = self.prepare_repo_root()
        example_path = repo_root / "config" / "config.example.ini"
        example_path.write_text(
            "[录制设置]\nfoo = demo\n\n[推送配置]\nbaz = demo\n",
            encoding="utf-8",
        )

        errors = compare_ini_structure(repo_root / "config" / "config.ini", example_path)

        self.assertEqual(
            ["{} 在 section [录制设置] 缺少 keys: bar".format(example_path)],
            errors,
        )

    def test_validate_url_example_requires_active_entry(self) -> None:
        repo_root = self.prepare_repo_root()
        url_example = repo_root / "config" / "URL_config.example.ini"
        url_example.write_text("# only comments\n\n", encoding="utf-8")

        errors = validate_url_example(url_example)

        self.assertEqual(
            [f"{url_example} 需要至少保留一条非注释示例地址，避免公开模板为空。"],
            errors,
        )

    def test_validate_config_examples_passes_for_synced_workspace(self) -> None:
        repo_root = self.prepare_repo_root()

        result = validate_config_examples(repo_root)

        self.assertTrue(result.ok)
        self.assertEqual([], result.errors)


if __name__ == "__main__":
    unittest.main()
