from __future__ import annotations

import shutil
import threading
import unittest
import urllib.parse
import urllib.request
from pathlib import Path
from uuid import uuid4

from client.infra.docker.config_web import DockerLogStore, UrlConfigStore, create_server


class DockerConfigWebTests(unittest.TestCase):
    def make_workspace(self, prefix: str) -> Path:
        root = Path.cwd() / f"{prefix}_{uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def stop_server(self, server, thread: threading.Thread) -> None:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    def test_store_append_toggle_delete_and_save_roundtrip(self) -> None:
        root = self.make_workspace("tmp_docker_config_store")
        config_path = root / "URL_config.ini"
        store = UrlConfigStore(config_path)

        store.append("https://live.douyin.com/123")
        store.append("https://www.showroom-live.com/room/456", quality="超清", name="主播A")
        store.toggle(0)
        store.delete(1)
        store.write_text("原画,https://live.douyin.com/789,主播B\n")

        self.assertEqual("原画,https://live.douyin.com/789,主播B\n", store.read_text())
        entries = store.list_lines()
        self.assertEqual(1, len(entries))
        self.assertTrue(entries[0].active)
        self.assertEqual("原画", entries[0].quality)
        self.assertEqual("https://live.douyin.com/789", entries[0].url)
        self.assertEqual("主播B", entries[0].name)

    def test_http_server_renders_and_adds_entry(self) -> None:
        root = self.make_workspace("tmp_docker_config_web")
        config_path = root / "URL_config.ini"
        log_dir = root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        config_path.write_text("https://live.douyin.com/123\n", encoding="utf-8-sig")
        (log_dir / "streamget.log").write_text("line 1\nline 2\n", encoding="utf-8")
        server = create_server(config_path=config_path, log_dir=log_dir, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.stop_server, server, thread)

        host, port = server.server_address
        home = urllib.request.urlopen(f"http://{host}:{port}/", timeout=5)
        home_body = home.read().decode("utf-8")
        self.assertIn("Docker 录制配置页", home_body)
        self.assertIn("https://live.douyin.com/123", home_body)

        payload = urllib.parse.urlencode(
            {
                "quality": "高清",
                "url": "https://live.douyin.com/456",
                "name": "主播C",
            }
        ).encode("utf-8")
        response = urllib.request.urlopen(
            urllib.request.Request(
                f"http://{host}:{port}/entries/add",
                data=payload,
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ),
            timeout=5,
        )
        response_body = response.read().decode("utf-8")

        self.assertIn("已添加主播配置", response_body)
        self.assertIn("主播C", response_body)
        content = config_path.read_text(encoding="utf-8-sig")
        self.assertIn("高清,https://live.douyin.com/456,主播C", content)

        logs_page = urllib.request.urlopen(f"http://{host}:{port}/logs?file=streamget.log&lines=100", timeout=5)
        logs_body = logs_page.read().decode("utf-8")
        self.assertIn("日志控制台", logs_body)
        self.assertIn("line 1", logs_body)

    def test_log_store_reads_tail_of_known_log(self) -> None:
        root = self.make_workspace("tmp_docker_log_store")
        log_dir = root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "streamget.log").write_text("a\nb\nc\n", encoding="utf-8")
        store = DockerLogStore(log_dir)

        file_name, content = store.tail("streamget.log", lines=2)

        self.assertEqual("streamget.log", file_name)
        self.assertEqual("b\nc", content)


if __name__ == "__main__":
    unittest.main()
