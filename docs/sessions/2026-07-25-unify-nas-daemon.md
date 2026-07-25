# NAS Web 与抖音 daemon 统一

日期：2026-07-25

## 范围

- NAS Web 与 daemon 共用 `config/douyin.yaml`、`HealthState` 和状态目录。
- 删除 NAS Launcher 对旧 `main.py` 与 `URL_config.ini` 的运行依赖。
- 增加 YAML 原子写入、配置热加载、Web Token、CSRF 和统一生命周期。
- 不修改旧多平台解析源码、Windows GUI 或抖音解析算法。

## 实现

- `YamlConfigStore` 只修改房间列表，并在临时文件校验成功后原子替换。
- daemon 以不可变 `AppConfig` 为快照，配置文件变化后原子切换；停用或删除房间
  由同一个 `ProcessManager` 停止对应 FFmpeg。
- Web 状态页直接读取 daemon 写入的 `health.json`；Healthcheck 不再扫描 `/proc`。
- Launcher 先停止 Web 写入，再通知 daemon，最终等待 Web 和录制线程退出。
- NAS Compose 通过 `/run/secrets/web_token` 和 `/run/secrets/douyin_cookie`
  挂载 Secret。

## 验证

- `python -m pytest -v`：151 项通过。
- `daemon` 与 `nas-web` 两个 Docker target 均使用指定命令构建成功。
- 三份 Compose 均通过 `docker compose ... config`。
- NAS 真实容器验证：
  - 未鉴权管理请求返回 401，带 Token 与 CSRF 的房间新增成功。
  - `started_at` 未变化，`configured_rooms` 和 `config_reloaded_at` 更新，确认热加载
    未重启 daemon。
  - NAS 进程中存在 `app.douyin_daemon` 且不存在 `main.py`。
  - Web、Healthcheck 和状态页读取同一 HealthState。
  - `docker stop` 后无 FFmpeg 残留，SIGINT 停止路径完成。
- FFmpeg 测试生成的 TS 已通过容器内 `ffprobe`。
- 旧多平台入口的编译检查和既有兼容测试通过。
- 231 个已跟踪文本文件通过严格 UTF-8 与明显乱码检查。

## 未执行

- 未执行真实飞牛 NAS 部署。
- 未执行 24/72 小时长期运行测试。
