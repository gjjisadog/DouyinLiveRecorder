from __future__ import annotations

import html
import os
import re
import threading
import urllib.parse
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

DEFAULT_CONFIG_PATH = Path("/app/config/URL_config.ini")
DEFAULT_LOG_DIR = Path("/app/logs")
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 18091
DEFAULT_QUALITY = "原画"
QUALITY_OPTIONS = ("原画", "蓝光", "超清", "高清", "标清", "流畅")
DEFAULT_LOG_FILE = "streamget.log"
DEFAULT_LOG_LINES = 200
MAX_LOG_LINES = 1000
LOG_FILES = ("streamget.log", "PlayURL.log")
URL_PATTERN = re.compile(r"(https?://)?(www\.)?[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+(:\d+)?(/.*)?")


@dataclass(frozen=True)
class UrlConfigLine:
    index: int
    line_no: int
    raw: str
    stripped: str
    active: bool
    quality: str
    url: str
    name: str
    has_content: bool


def contains_url(value: str) -> bool:
    return bool(URL_PATTERN.search(value.strip()))


def split_fields(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[，,]", value.strip(), maxsplit=2)]


def parse_fields(value: str) -> tuple[str, str, str]:
    normalized = value.strip()
    if not normalized:
        return "", "", ""

    parts = split_fields(normalized)
    if len(parts) == 1:
        return "", parts[0], ""
    if len(parts) == 2:
        if contains_url(parts[0]):
            return "", parts[0], parts[1]
        return parts[0], parts[1], ""
    quality, url, name = parts[:3]
    return quality, url, name


def build_line(url: str, quality: str = "", name: str = "") -> str:
    url = url.strip()
    quality = quality.strip()
    name = name.strip()
    if not url:
        raise ValueError("直播间地址不能为空")
    if quality and name:
        return f"{quality},{url},{name}"
    if quality:
        return f"{quality},{url}"
    if name:
        return f"{url},{name}"
    return url


class UrlConfigStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def ensure_file(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8-sig")

    def read_text(self) -> str:
        self.ensure_file()
        return self.path.read_text(encoding="utf-8-sig")

    def write_text(self, content: str) -> None:
        normalized = content.replace("\r\n", "\n")
        self.ensure_file()
        with self._lock:
            self.path.write_text(normalized, encoding="utf-8-sig")

    def list_lines(self) -> list[UrlConfigLine]:
        text = self.read_text()
        entries: list[UrlConfigLine] = []
        for index, raw in enumerate(text.splitlines()):
            stripped = raw.strip()
            if not stripped:
                continue
            active = not stripped.startswith("#")
            body = stripped if active else stripped[1:].strip()
            quality, url, name = parse_fields(body)
            entries.append(
                UrlConfigLine(
                    index=index,
                    line_no=index + 1,
                    raw=raw,
                    stripped=body,
                    active=active,
                    quality=quality,
                    url=url,
                    name=name,
                    has_content=bool(body),
                )
            )
        return entries

    def append(self, url: str, quality: str = "", name: str = "") -> None:
        new_line = build_line(url=url, quality=quality, name=name)
        self.ensure_file()
        with self._lock:
            current = self.path.read_text(encoding="utf-8-sig")
            normalized = current.replace("\r\n", "\n")
            if normalized and not normalized.endswith("\n"):
                normalized += "\n"
            normalized += f"{new_line}\n"
            self.path.write_text(normalized, encoding="utf-8-sig")

    def _update_line(self, target_index: int, transform: Callable[[str], str | None]) -> None:
        self.ensure_file()
        with self._lock:
            lines = self.path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").splitlines()
            if target_index < 0 or target_index >= len(lines):
                raise IndexError("配置行不存在")
            replacement = transform(lines[target_index])
            if replacement is None:
                del lines[target_index]
            else:
                lines[target_index] = replacement
            content = "\n".join(lines)
            if content:
                content += "\n"
            self.path.write_text(content, encoding="utf-8-sig")

    def toggle(self, target_index: int) -> None:
        def transform(raw: str) -> str:
            stripped = raw.lstrip()
            indent = raw[: len(raw) - len(stripped)]
            if stripped.startswith("#"):
                uncommented = stripped[1:]
                return indent + uncommented.lstrip()
            return f"{indent}# {stripped}" if stripped else raw

        self._update_line(target_index, transform)

    def delete(self, target_index: int) -> None:
        self._update_line(target_index, lambda _: None)


class DockerLogStore:
    def __init__(self, log_dir: Path) -> None:
        self.log_dir = log_dir

    def file_path(self, file_name: str) -> Path:
        safe_name = Path(file_name).name
        return self.log_dir / safe_name

    def available_logs(self) -> list[str]:
        names: list[str] = []
        for file_name in LOG_FILES:
            path = self.file_path(file_name)
            if path.exists():
                names.append(file_name)
        if names:
            return names
        return list(LOG_FILES)

    def tail(self, file_name: str, lines: int = DEFAULT_LOG_LINES) -> tuple[str, str]:
        selected = Path(file_name).name
        if selected not in LOG_FILES:
            raise ValueError("日志文件不存在")
        line_limit = max(1, min(lines, MAX_LOG_LINES))
        path = self.file_path(selected)
        if not path.exists():
            return selected, ""
        content = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return selected, "\n".join(content[-line_limit:])


def render_shell_link(active_path: str) -> str:
    links = [
        ("/", "主播配置"),
        ("/logs", "日志控制台"),
    ]
    items: list[str] = []
    for path, label in links:
        css_class = "nav-link active" if path == active_path else "nav-link"
        items.append(f'<a class="{css_class}" href="{path}">{html.escape(label)}</a>')
    return "".join(items)


def render_layout(title: str, subtitle: str, body: str, notice: str = "", active_path: str = "/") -> str:
    nav_html = render_shell_link(active_path=active_path)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #eef3f1;
      --panel: #ffffff;
      --text: #17322c;
      --muted: #5c746c;
      --line: #d6e0dc;
      --accent: #0c8b6d;
      --accent-dark: #06624d;
      --danger: #c53f3f;
      --danger-dark: #912b2b;
      --error-bg: #fff1f1;
      --ok-bg: #eefaf5;
      --nav-bg: rgba(255, 255, 255, 0.14);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top right, rgba(12, 139, 109, 0.12), transparent 24rem),
        linear-gradient(180deg, #f7fbfa 0%, var(--bg) 100%);
    }}
    .page {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 24px 16px 48px;
    }}
    .hero {{
      background: linear-gradient(135deg, #12352f 0%, #0c8b6d 100%);
      color: #fff;
      border-radius: 20px;
      padding: 24px;
      box-shadow: 0 20px 60px rgba(18, 53, 47, 0.15);
    }}
    .hero h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .hero p {{ margin: 0; color: rgba(255, 255, 255, 0.88); line-height: 1.6; }}
    .nav {{
      display: flex;
      gap: 12px;
      margin-top: 18px;
      flex-wrap: wrap;
    }}
    .nav-link {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border-radius: 999px;
      text-decoration: none;
      color: #fff;
      background: var(--nav-bg);
      border: 1px solid rgba(255, 255, 255, 0.18);
      font-weight: 700;
    }}
    .nav-link.active {{
      background: #fff;
      color: var(--accent-dark);
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 18px;
      margin-top: 18px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid rgba(12, 139, 109, 0.12);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 12px 32px rgba(23, 50, 44, 0.06);
    }}
    .card h2 {{ margin: 0 0 12px; font-size: 18px; }}
    .card p, .hint {{ color: var(--muted); line-height: 1.6; }}
    .notice {{
      margin: 18px 0 0;
      padding: 12px 14px;
      border-radius: 12px;
      font-weight: 600;
    }}
    .notice.success {{ background: var(--ok-bg); color: var(--accent-dark); }}
    .notice.error {{ background: var(--error-bg); color: var(--danger-dark); }}
    .form-grid {{
      display: grid;
      grid-template-columns: 160px 1fr 220px auto;
      gap: 12px;
      align-items: end;
    }}
    .toolbar {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: end;
    }}
    .toolbar .field {{
      min-width: 180px;
      flex: 1;
    }}
    label {{
      display: block;
      font-size: 13px;
      font-weight: 700;
      margin-bottom: 6px;
    }}
    input, select, textarea, button {{
      width: 100%;
      border-radius: 12px;
      border: 1px solid var(--line);
      padding: 10px 12px;
      font: inherit;
    }}
    textarea {{
      min-height: 260px;
      resize: vertical;
      font-family: Consolas, "Courier New", monospace;
      line-height: 1.5;
    }}
    button {{
      cursor: pointer;
      border: none;
      background: var(--accent);
      color: #fff;
      font-weight: 700;
    }}
    button:hover {{ background: var(--accent-dark); }}
    button.danger {{ background: var(--danger); }}
    button.danger:hover {{ background: var(--danger-dark); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
    }}
    th, td {{
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    .raw, .url {{
      word-break: break-all;
      font-family: Consolas, "Courier New", monospace;
    }}
    .actions {{
      display: flex;
      gap: 8px;
      min-width: 160px;
    }}
    .actions form {{ flex: 1; }}
    .active td:first-child {{ color: var(--accent-dark); font-weight: 700; }}
    .inactive td:first-child {{ color: var(--muted); }}
    .empty {{
      text-align: center;
      color: var(--muted);
      padding: 24px 0;
    }}
    .footer {{
      margin-top: 12px;
      font-size: 13px;
      color: var(--muted);
    }}
    .console {{
      margin-top: 14px;
      min-height: 420px;
      padding: 16px;
      border-radius: 16px;
      background: #112922;
      color: #d7f4ea;
      font-family: Consolas, "Courier New", monospace;
      font-size: 13px;
      line-height: 1.55;
      white-space: pre-wrap;
      word-break: break-word;
      overflow: auto;
      border: 1px solid rgba(12, 139, 109, 0.18);
    }}
    .console-empty {{
      color: #8fb4a8;
    }}
    @media (max-width: 960px) {{
      .form-grid {{
        grid-template-columns: 1fr;
      }}
      .actions {{
        flex-direction: column;
        min-width: 120px;
      }}
      table, thead, tbody, th, td, tr {{
        display: block;
      }}
      thead {{ display: none; }}
      tr {{
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 12px;
        margin-bottom: 12px;
      }}
      td {{
        border: none;
        padding: 6px 0;
      }}
      .toolbar {{
        flex-direction: column;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>{html.escape(title)}</h1>
      <p>{subtitle}</p>
      {notice}
      <div class="nav">{nav_html}</div>
    </section>
    <div class="grid">
      {body}
    </div>
  </div>
</body>
</html>
"""


def render_page(store: UrlConfigStore, message: str = "", error: str = "") -> str:
    entries = store.list_lines()
    raw_text = store.read_text()
    notice = ""
    if error:
        notice = f'<div class="notice error">{html.escape(error)}</div>'
    elif message:
        notice = f'<div class="notice success">{html.escape(message)}</div>'

    rows: list[str] = []
    for entry in entries:
        status_text = "启用中" if entry.active else "已停用"
        quality_text = entry.quality or "默认"
        url_text = entry.url or "-"
        name_text = entry.name or "-"
        row_class = "active" if entry.active else "inactive"
        rows.append(
            f"""
            <tr class="{row_class}">
              <td>{entry.line_no}</td>
              <td>{html.escape(status_text)}</td>
              <td>{html.escape(quality_text)}</td>
              <td class="url">{html.escape(url_text)}</td>
              <td>{html.escape(name_text)}</td>
              <td class="raw">{html.escape(entry.raw)}</td>
              <td class="actions">
                <form method="post" action="/entries/{entry.index}/toggle">
                  <button type="submit">{'停用' if entry.active else '启用'}</button>
                </form>
                <form method="post" action="/entries/{entry.index}/delete" onsubmit="return confirm('确认删除这一行配置？');">
                  <button type="submit" class="danger">删除</button>
                </form>
              </td>
            </tr>
            """
        )

    entries_html = "\n".join(rows) if rows else '<tr><td colspan="7" class="empty">当前还没有任何主播配置</td></tr>'
    quality_options = ['<option value="">默认画质</option>']
    for option in QUALITY_OPTIONS:
        quality_options.append(f'<option value="{html.escape(option)}">{html.escape(option)}</option>')

    body = f"""
      <section class="card">
        <h2>添加主播</h2>
        <form method="post" action="/entries/add" class="form-grid">
          <div>
            <label for="quality">单独画质</label>
            <select id="quality" name="quality">
              {"".join(quality_options)}
            </select>
          </div>
          <div>
            <label for="url">直播间地址</label>
            <input id="url" name="url" type="text" placeholder="https://live.douyin.com/xxxx" required>
          </div>
          <div>
            <label for="name">自定义主播名</label>
            <input id="name" name="name" type="text" placeholder="可选">
          </div>
          <div>
            <label>&nbsp;</label>
            <button type="submit">添加到列表</button>
          </div>
        </form>
        <p class="hint">支持格式：仅地址、画质+地址、画质+地址+主播名。页面添加时会自动生成正确的配置行。</p>
      </section>

      <section class="card">
        <h2>当前主播列表</h2>
        <table>
          <thead>
            <tr>
              <th>行号</th>
              <th>状态</th>
              <th>画质</th>
              <th>地址</th>
              <th>主播名</th>
              <th>原始配置</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {entries_html}
          </tbody>
        </table>
        <div class="footer">“停用” 等同于给这一行前面加 <code>#</code>，“删除” 会直接移除这行配置。</div>
      </section>

      <section class="card">
        <h2>原始配置编辑</h2>
        <form method="post" action="/config/save">
          <label for="content">完整内容</label>
          <textarea id="content" name="content" spellcheck="false">{html.escape(raw_text)}</textarea>
          <p class="hint">适合批量粘贴主播地址，或手动保留注释与自定义格式。</p>
          <button type="submit">保存整个配置文件</button>
        </form>
      </section>
"""
    return render_layout(
        title="Docker 录制配置页",
        subtitle=f"这里直接管理 <code>{html.escape(str(store.path))}</code>。保存后会写入容器挂载的配置文件，录制主进程会在后续循环里自动读取新的主播列表。",
        body=body,
        notice=notice,
        active_path="/",
    )


def render_logs_page(
    log_store: DockerLogStore,
    selected_file: str = DEFAULT_LOG_FILE,
    line_count: int = DEFAULT_LOG_LINES,
    message: str = "",
    error: str = "",
) -> str:
    notice = ""
    if error:
        notice = f'<div class="notice error">{html.escape(error)}</div>'
    elif message:
        notice = f'<div class="notice success">{html.escape(message)}</div>'
    file_name, content = log_store.tail(selected_file, lines=line_count)
    file_options: list[str] = []
    for item in log_store.available_logs():
        selected = " selected" if item == file_name else ""
        file_options.append(f'<option value="{html.escape(item)}"{selected}>{html.escape(item)}</option>')
    line_options = []
    selected_line_count = max(1, min(line_count, MAX_LOG_LINES))
    for option in (100, 200, 500, 1000):
        selected = " selected" if option == selected_line_count else ""
        line_options.append(f'<option value="{option}"{selected}>{option} 行</option>')
    content_html = html.escape(content) if content else '<span class="console-empty">当前日志文件为空，或还没有生成日志。</span>'
    body = f"""
      <section class="card">
        <h2>日志控制台</h2>
        <form method="get" action="/logs" class="toolbar">
          <div class="field">
            <label for="file">日志文件</label>
            <select id="file" name="file">
              {"".join(file_options)}
            </select>
          </div>
          <div class="field">
            <label for="lines">显示行数</label>
            <select id="lines" name="lines">
              {"".join(line_options)}
            </select>
          </div>
          <div class="field">
            <label>&nbsp;</label>
            <button type="submit">刷新日志</button>
          </div>
        </form>
        <p class="hint">该页面直接读取容器挂载的 <code>/app/logs</code> 目录，适合通过 FN Connect 查看当前录制状态、错误和播放地址日志。</p>
        <div class="console">{content_html}</div>
      </section>
    """
    return render_layout(
        title="Docker 日志控制台",
        subtitle="这里展示容器内录制日志的最新内容，适合通过 FN Connect 远程查看运行状态。",
        body=body,
        notice=notice,
        active_path="/logs",
    )


class ConfigRequestHandler(BaseHTTPRequestHandler):
    server_version = "DouyinLiveRecorderConfigWeb/1.0"

    @property
    def store(self) -> UrlConfigStore:
        return self.server.store  # type: ignore[attr-defined]

    @property
    def log_store(self) -> DockerLogStore:
        return self.server.log_store  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if parsed.path == "/":
            content = render_page(
                self.store,
                message=query.get("message", [""])[0],
                error=query.get("error", [""])[0],
            )
            self._write_html(content)
            return
        if parsed.path == "/logs":
            try:
                requested_lines = int(query.get("lines", [str(DEFAULT_LOG_LINES)])[0])
            except ValueError:
                requested_lines = DEFAULT_LOG_LINES
            try:
                content = render_logs_page(
                    self.log_store,
                    selected_file=query.get("file", [DEFAULT_LOG_FILE])[0],
                    line_count=requested_lines,
                    message=query.get("message", [""])[0],
                    error=query.get("error", [""])[0],
                )
            except ValueError as exc:
                content = render_logs_page(self.log_store, error=str(exc))
            self._write_html(content)
            return
        if parsed.path == "/health":
            self._write_text(HTTPStatus.OK, "ok")
            return
        self._write_text(HTTPStatus.NOT_FOUND, "not found")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        try:
            form = self._read_form()
            if parsed.path == "/entries/add":
                self.store.append(
                    url=form.get("url", ""),
                    quality=form.get("quality", ""),
                    name=form.get("name", ""),
                )
                self._redirect_with_message("已添加主播配置")
                return
            if parsed.path == "/config/save":
                self.store.write_text(form.get("content", ""))
                self._redirect_with_message("已保存配置文件")
                return
            match = re.fullmatch(r"/entries/(\d+)/(toggle|delete)", parsed.path)
            if match:
                target_index = int(match.group(1))
                action = match.group(2)
                if action == "toggle":
                    self.store.toggle(target_index)
                    self._redirect_with_message("已更新主播启用状态")
                    return
                if action == "delete":
                    self.store.delete(target_index)
                    self._redirect_with_message("已删除该行配置")
                    return
            self._write_text(HTTPStatus.NOT_FOUND, "not found")
        except (IndexError, ValueError) as exc:
            self._redirect_with_error(str(exc))

    def log_message(self, format: str, *args: object) -> None:
        print(f"[docker-config-web] {self.address_string()} - {format % args}")

    def _read_form(self) -> dict[str, str]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8", errors="ignore")
        parsed = urllib.parse.parse_qs(raw_body, keep_blank_values=True)
        return {key: values[0] for key, values in parsed.items()}

    def _write_html(self, content: str) -> None:
        body = content.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_text(self, status: HTTPStatus, content: str) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect_with_message(self, message: str) -> None:
        self._redirect("/", message=message)

    def _redirect_with_error(self, error: str) -> None:
        self._redirect("/", error=error)

    def _redirect(self, path: str, **query: str) -> None:
        target = path
        if query:
            target = f"{path}?{urllib.parse.urlencode(query)}"
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", target)
        self.send_header("Content-Length", "0")
        self.end_headers()


class ConfigWebServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], store: UrlConfigStore, log_store: DockerLogStore) -> None:
        super().__init__(server_address, ConfigRequestHandler)
        self.store = store
        self.log_store = log_store


def create_server(
    config_path: Path = DEFAULT_CONFIG_PATH,
    log_dir: Path = DEFAULT_LOG_DIR,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> ConfigWebServer:
    store = UrlConfigStore(config_path)
    store.ensure_file()
    log_store = DockerLogStore(log_dir)
    return ConfigWebServer((host, port), store, log_store)


def resolve_bind_address() -> tuple[str, int, Path, Path]:
    host = os.environ.get("DLR_WEB_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
    port = int(os.environ.get("DLR_WEB_PORT", str(DEFAULT_PORT)))
    config_path = Path(os.environ.get("DLR_WEB_CONFIG_PATH", str(DEFAULT_CONFIG_PATH)))
    log_dir = Path(os.environ.get("DLR_WEB_LOG_DIR", str(DEFAULT_LOG_DIR)))
    return host, port, config_path, log_dir


def main() -> int:
    host, port, config_path, log_dir = resolve_bind_address()
    server = create_server(config_path=config_path, log_dir=log_dir, host=host, port=port)
    print(f"[docker-config-web] serving http://{host}:{port} for {config_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
