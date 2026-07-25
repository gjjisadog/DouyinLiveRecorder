from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app.config import ConfigError
from app.config_store import ManagedRoom, YamlConfigStore
from app.health import check as check_daemon_health
from app.health import read_health_state

DEFAULT_CONFIG_PATH = Path("/app/config/douyin.yaml")
DEFAULT_LOG_DIR = Path("/app/logs")
DEFAULT_STATE_PATH = Path("/data/state")
DEFAULT_TOKEN_FILE = Path("/run/secrets/web_token")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18091
DEFAULT_LOG_FILE = "streamget.log"
DEFAULT_LOG_LINES = 200
MAX_LOG_LINES = 1000
MAX_REQUEST_BODY = 64 * 1024
LOG_FILES = ("streamget.log", "PlayURL.log")
QUALITY_OPTIONS = ("original", "uhd", "hd", "sd", "ld")
PUBLIC_HOSTS = {"0.0.0.0", "::", "[::]"}


class DockerLogStore:
    def __init__(self, log_dir: Path) -> None:
        self.log_dir = log_dir

    def available_logs(self) -> list[str]:
        available = [name for name in LOG_FILES if (self.log_dir / name).is_file()]
        return available or list(LOG_FILES)

    def tail(self, file_name: str, lines: int = DEFAULT_LOG_LINES) -> tuple[str, str]:
        selected = Path(file_name).name
        if selected not in LOG_FILES:
            raise ValueError("日志文件不存在")
        limit = max(1, min(lines, MAX_LOG_LINES))
        path = self.log_dir / selected
        if not path.is_file():
            return selected, ""
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return selected, "\n".join(content[-limit:])


def _read_token(path: Path) -> str:
    try:
        token = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"无法读取 DLR_WEB_TOKEN_FILE: {path}: {exc}") from exc
    if len(token) < 16 or "\n" in token or "\r" in token:
        raise RuntimeError("Web Token 至少需要 16 个单行字符")
    return token


def _is_authorized(header: str, expected: str) -> bool:
    if not expected:
        return True
    candidate = ""
    if header.startswith("Bearer "):
        candidate = header[7:].strip()
    elif header.startswith("Basic "):
        try:
            decoded = base64.b64decode(header[6:].strip(), validate=True).decode("utf-8")
            _, candidate = decoded.split(":", 1)
        except (ValueError, UnicodeError):
            candidate = ""
    return hmac.compare_digest(candidate, expected)


def _csrf_field(token: str) -> str:
    return f'<input type="hidden" name="csrf_token" value="{html.escape(token)}">'


def _layout(title: str, body: str, notice: str = "") -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin:0; background:#eef3f1; color:#17322c; font-family:system-ui,"Microsoft YaHei",sans-serif; }}
    main {{ max-width:1180px; margin:auto; padding:24px 16px 48px; }}
    header {{ padding:22px; border-radius:18px; color:#fff; background:linear-gradient(135deg,#12352f,#0c8b6d); }}
    nav a {{ color:#fff; margin-right:16px; }}
    section {{ margin-top:18px; padding:18px; border-radius:16px; background:#fff; box-shadow:0 8px 28px #17322c12; }}
    table {{ width:100%; border-collapse:collapse; }}
    th,td {{ padding:9px 7px; border-bottom:1px solid #d6e0dc; text-align:left; vertical-align:top; }}
    input,select,button {{ width:100%; padding:9px; border:1px solid #cbd8d3; border-radius:9px; }}
    button {{ color:#fff; background:#0c8b6d; border:0; cursor:pointer; }}
    button.danger {{ background:#b63232; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }}
    .actions {{ display:grid; grid-template-columns:1fr 1fr; gap:6px; min-width:140px; }}
    .notice {{ margin-top:12px; padding:10px; border-radius:8px; background:#eefaf5; }}
    .error {{ background:#fff1f1; color:#8b2020; }}
    .status {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }}
    .metric {{ padding:12px; border-radius:10px; background:#f4f8f6; }}
    code,pre {{ word-break:break-all; }}
    @media(max-width:850px) {{ .grid,.status {{ grid-template-columns:1fr; }} table,tbody,tr,td {{ display:block; }} thead {{ display:none; }} }}
  </style>
</head>
<body><main>
  <header><h1>{html.escape(title)}</h1><nav><a href="/">房间与状态</a><a href="/logs">日志</a></nav>{notice}</header>
  {body}
</main></body></html>"""


def _room_form(room: ManagedRoom, csrf_token: str) -> str:
    options = "".join(
        f'<option value="{quality}"{" selected" if quality == room.quality else ""}>{quality}</option>'
        for quality in QUALITY_OPTIONS
    )
    return f"""
      <form method="post" action="/rooms/{room.index}/update">
        {_csrf_field(csrf_token)}
        <div class="grid">
          <input name="url" value="{html.escape(room.url)}" required>
          <input name="name" value="{html.escape(room.name)}" placeholder="主播名">
          <select name="quality">{options}</select>
          <label><input type="checkbox" name="enabled" value="1"{" checked" if room.enabled else ""}> 启用</label>
        </div>
        <button type="submit">保存修改</button>
      </form>"""


def render_page(
    store: YamlConfigStore,
    state_path: Path,
    csrf_token: str,
    *,
    message: str = "",
    error: str = "",
) -> str:
    rooms = store.list_rooms()
    settings = store.recorder_settings()
    try:
        state = read_health_state(state_path)
        healthy, health_message = check_daemon_health(store.path, state_path)
    except ValueError as exc:
        state = {}
        healthy, health_message = False, str(exc)
    notice = ""
    if error:
        notice = f'<div class="notice error">{html.escape(error)}</div>'
    elif message:
        notice = f'<div class="notice">{html.escape(message)}</div>'
    health_class = "" if healthy else " error"
    status = f"""
    <section>
      <h2>daemon 真实状态</h2>
      <div class="status">
        <div class="metric{health_class}"><b>服务健康</b><br>{html.escape(health_message)}</div>
        <div class="metric"><b>配置房间数</b><br>{int(state.get("configured_rooms", len(rooms)))}</div>
        <div class="metric"><b>正在录制</b><br>{int(state.get("active_recordings", 0))}</div>
        <div class="metric"><b>最近检测</b><br>{float(state.get("last_check_at", 0)):.3f}</div>
        <div class="metric"><b>磁盘剩余</b><br>{float(state.get("disk_free_gb", 0)):.2f} GiB</div>
        <div class="metric"><b>最近错误分类</b><br>{html.escape(str(state.get("last_error_category") or "-"))}</div>
        <div class="metric"><b>FFmpeg 返回状态</b><br>{html.escape(str(state.get("last_ffmpeg_return_code")))}</div>
        <div class="metric"><b>配置热加载错误</b><br>{html.escape(str(state.get("config_reload_error") or "-"))}</div>
      </div>
    </section>"""
    rows: list[str] = []
    for room in rooms:
        rows.append(
            f"""<tr>
              <td>{room.index + 1}</td><td>{_room_form(room, csrf_token)}</td>
              <td class="actions">
                <form method="post" action="/rooms/{room.index}/toggle">{_csrf_field(csrf_token)}<button>切换状态</button></form>
                <form method="post" action="/rooms/{room.index}/delete">{_csrf_field(csrf_token)}<button class="danger">删除</button></form>
              </td>
            </tr>"""
        )
    quality_options = "".join(f'<option value="{item}">{item}</option>' for item in QUALITY_OPTIONS)
    rooms_html = "".join(rows) or '<tr><td colspan="3">尚未配置房间，可直接添加，无需重启容器。</td></tr>'
    settings_html = "".join(
        f"<li><code>{html.escape(key)}</code>: {html.escape(str(value))}</li>"
        for key, value in settings.items()
    )
    body = f"""
      {status}
      <section><h2>添加抖音房间</h2>
        <form method="post" action="/rooms/add">
          {_csrf_field(csrf_token)}
          <div class="grid">
            <input name="url" placeholder="https://live.douyin.com/..." required>
            <input name="name" placeholder="主播名（可选）">
            <select name="quality">{quality_options}</select>
            <label><input type="checkbox" name="enabled" value="1" checked> 启用</label>
          </div><button type="submit">添加房间</button>
        </form>
      </section>
      <section><h2>房间配置</h2><table><thead><tr><th>#</th><th>配置</th><th>操作</th></tr></thead>
        <tbody>{rooms_html}</tbody></table></section>
      <section><h2>基础录制参数（只读）</h2><ul>{settings_html}</ul>
        <p>Cookie 仅从 <code>DOUYIN_COOKIE_FILE</code> 读取，本页面不会展示或写入 Cookie。</p></section>
    """
    return _layout("Douyin daemon NAS 管理", body, notice)


def render_logs_page(log_store: DockerLogStore, csrf_token: str, file_name: str, lines: int) -> str:
    selected, content = log_store.tail(file_name, lines)
    options = "".join(
        f'<option value="{html.escape(item)}"{" selected" if item == selected else ""}>{html.escape(item)}</option>'
        for item in log_store.available_logs()
    )
    body = f"""<section><h2>日志控制台</h2>
      <form method="get" action="/logs"><select name="file">{options}</select>
      <input name="lines" type="number" min="1" max="{MAX_LOG_LINES}" value="{lines}"><button>刷新</button></form>
      <pre>{html.escape(content)}</pre></section>"""
    return _layout("NAS 日志", body)


class ConfigRequestHandler(BaseHTTPRequestHandler):
    server_version = "DouyinLiveRecorderConfigWeb/2.0"

    @property
    def store(self) -> YamlConfigStore:
        return self.server.store  # type: ignore[attr-defined]

    def _authorized(self) -> bool:
        expected = self.server.web_token  # type: ignore[attr-defined]
        if _is_authorized(self.headers.get("Authorization", ""), expected):
            return True
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", 'Basic realm="Douyin Live Recorder"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def _csrf_valid(self, form: dict[str, str]) -> bool:
        expected = self.server.csrf_token  # type: ignore[attr-defined]
        cookie = self.headers.get("Cookie", "")
        match = re.search(r"(?:^|;\s*)dlr_csrf=([^;]+)", cookie)
        cookie_value = urllib.parse.unquote(match.group(1)) if match else ""
        return hmac.compare_digest(form.get("csrf_token", ""), expected) and hmac.compare_digest(
            cookie_value, expected
        )

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            healthy, message = check_daemon_health(
                self.store.path,
                self.server.state_path,  # type: ignore[attr-defined]
            )
            self._write_json(
                HTTPStatus.OK if healthy else HTTPStatus.SERVICE_UNAVAILABLE,
                {"healthy": healthy, "message": message},
            )
            return
        if not self._authorized():
            return
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if parsed.path == "/":
            try:
                page = render_page(
                    self.store,
                    self.server.state_path,  # type: ignore[attr-defined]
                    self.server.csrf_token,  # type: ignore[attr-defined]
                    message=query.get("message", [""])[0],
                    error=query.get("error", [""])[0],
                )
            except (ConfigError, OSError, ValueError) as exc:
                page = _layout("配置错误", "", f'<div class="notice error">{html.escape(str(exc))}</div>')
            self._write_html(page, set_csrf=True)
            return
        if parsed.path == "/logs":
            try:
                lines = int(query.get("lines", [str(DEFAULT_LOG_LINES)])[0])
                page = render_logs_page(
                    self.server.log_store,  # type: ignore[attr-defined]
                    self.server.csrf_token,  # type: ignore[attr-defined]
                    query.get("file", [DEFAULT_LOG_FILE])[0],
                    lines,
                )
            except (ValueError, OSError) as exc:
                page = _layout("日志错误", "", f'<div class="notice error">{html.escape(str(exc))}</div>')
            self._write_html(page, set_csrf=True)
            return
        self._write_text(HTTPStatus.NOT_FOUND, "not found")

    def do_POST(self) -> None:
        if not self._authorized():
            return
        if not self.server.accepting_writes:  # type: ignore[attr-defined]
            self._write_text(HTTPStatus.SERVICE_UNAVAILABLE, "server is stopping")
            return
        try:
            form = self._read_form()
        except ValueError as exc:
            self._write_text(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, str(exc))
            return
        if not self._csrf_valid(form):
            self._write_text(HTTPStatus.FORBIDDEN, "invalid CSRF token")
            return
        parsed = urllib.parse.urlparse(self.path)
        try:
            if parsed.path == "/rooms/add":
                self.store.add(
                    url=form.get("url", ""),
                    name=form.get("name", ""),
                    quality=form.get("quality", "original"),
                    enabled=form.get("enabled") == "1",
                )
                self._redirect("/", message="已添加房间，daemon 将自动热加载")
                return
            match = re.fullmatch(r"/rooms/(\d+)/(update|toggle|delete)", parsed.path)
            if not match:
                self._write_text(HTTPStatus.NOT_FOUND, "not found")
                return
            index = int(match.group(1))
            action = match.group(2)
            if action == "update":
                self.store.update(
                    index,
                    url=form.get("url", ""),
                    name=form.get("name", ""),
                    quality=form.get("quality", "original"),
                    enabled=form.get("enabled") == "1",
                )
            elif action == "toggle":
                self.store.toggle(index)
            else:
                self.store.delete(index)
            self._redirect("/", message="配置已保存，daemon 将自动热加载")
        except (ConfigError, IndexError, OSError, ValueError) as exc:
            self._redirect("/", error=str(exc))

    def _read_form(self) -> dict[str, str]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length < 0 or length > MAX_REQUEST_BODY:
            raise ValueError(f"request body exceeds {MAX_REQUEST_BODY} bytes")
        body = self.rfile.read(length).decode("utf-8", errors="strict")
        parsed = urllib.parse.parse_qs(body, keep_blank_values=True, max_num_fields=32)
        return {key: values[0] for key, values in parsed.items()}

    def _write_html(self, content: str, *, set_csrf: bool = False) -> None:
        body = content.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        if set_csrf:
            token = urllib.parse.quote(self.server.csrf_token)  # type: ignore[attr-defined]
            self.send_header("Set-Cookie", f"dlr_csrf={token}; Path=/; SameSite=Strict; HttpOnly")
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

    def _write_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, path: str, **query: str) -> None:
        target = f"{path}?{urllib.parse.urlencode(query)}" if query else path
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", target)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        path = urllib.parse.urlparse(self.path).path
        digest = hashlib.sha256(self.client_address[0].encode("utf-8")).hexdigest()[:8]
        print(f"[docker-config-web] client={digest} method={self.command} path={path}")


class ConfigWebServer(ThreadingHTTPServer):
    daemon_threads = False
    block_on_close = True

    def __init__(
        self,
        server_address: tuple[str, int],
        store: YamlConfigStore,
        log_store: DockerLogStore,
        state_path: Path,
        web_token: str,
    ) -> None:
        super().__init__(server_address, ConfigRequestHandler)
        self.store = store
        self.log_store = log_store
        self.state_path = state_path
        self.web_token = web_token
        self.csrf_token = secrets.token_urlsafe(32)
        self.accepting_writes = True

    def stop_accepting_writes(self) -> None:
        self.accepting_writes = False


def create_server(
    config_path: Path = DEFAULT_CONFIG_PATH,
    log_dir: Path = DEFAULT_LOG_DIR,
    state_path: Path = DEFAULT_STATE_PATH,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    token: str | None = None,
    token_file: Path | None = None,
) -> ConfigWebServer:
    resolved_token = token
    if resolved_token is None and token_file is not None:
        resolved_token = _read_token(token_file)
    resolved_token = resolved_token or ""
    if host in PUBLIC_HOSTS and not resolved_token:
        raise RuntimeError("拒绝在公网地址启动未鉴权 Web；请设置 DLR_WEB_TOKEN_FILE")
    store = YamlConfigStore(config_path)
    store.ensure_file()
    return ConfigWebServer(
        (host, port),
        store,
        DockerLogStore(log_dir),
        state_path,
        resolved_token,
    )


def resolve_bind_address() -> tuple[str, int, Path, Path, Path, Path]:
    host = os.environ.get("DLR_WEB_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
    port = int(os.environ.get("DLR_WEB_PORT", str(DEFAULT_PORT)))
    config_path = Path(os.environ.get("DOUYIN_CONFIG", str(DEFAULT_CONFIG_PATH)))
    log_dir = Path(os.environ.get("DLR_WEB_LOG_DIR", str(DEFAULT_LOG_DIR)))
    state_path = Path(os.environ.get("DLR_STATE_PATH", str(DEFAULT_STATE_PATH)))
    token_file = Path(os.environ.get("DLR_WEB_TOKEN_FILE", str(DEFAULT_TOKEN_FILE)))
    return host, port, config_path, log_dir, state_path, token_file


def main() -> int:
    host, port, config_path, log_dir, state_path, token_file = resolve_bind_address()
    server = create_server(
        config_path=config_path,
        log_dir=log_dir,
        state_path=state_path,
        host=host,
        port=port,
        token_file=token_file,
    )
    print(f"[docker-config-web] serving host={host} port={port} config={config_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop_accepting_writes()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
