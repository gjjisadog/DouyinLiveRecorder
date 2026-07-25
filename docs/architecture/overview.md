# 架构概览

最后更新：2026-07-25

## 运行入口

| 模式 | 入口 | 主要配置 | 输出与状态 |
| --- | --- | --- | --- |
| 旧多平台 CLI | `python main.py` | `config/config.ini`、`config/URL_config.ini` | `downloads/`、`logs/` |
| Windows 客户端 | `python client/main.py` | `client_data/` 与兼容 INI | GUI、历史数据库、录制文件 |
| Docker daemon | `python -m app.douyin_daemon` | `config/douyin.yaml`、Cookie Secret | `/data/downloads`、`/data/state` |
| 飞牛 NAS Web | `python -m client.infra.docker.launcher` | `config/douyin.yaml`、Cookie/Web Token Secret | Web 18091、`/data/downloads`、`/data/state` |

## 代码边界

- `src/`：各直播平台解析与旧录制链路共享实现。
- `app/`：抖音无头调度、配置校验、健康状态、身份缓存、FFmpeg 管理和可选 remux。
- `client/core/`：桌面端业务服务。
- `client/ui/`、`client/viewmodels/`：PySide6 展示与交互。
- `client/infra/docker/`：NAS Web、Launcher、Healthcheck、构建发布和部署回归。
- `tests/`：daemon 与媒体进程测试。
- `client/tests/`：客户端及 Docker 适配测试。

## Docker 构建

Dockerfile 提供共享运行时层和两个明确 target：

- `daemon`：仅启动无头 daemon，使用 `app.health`，不暴露 Web 端口。
- `nas-web`：启动 Docker Launcher，同时运行轻量 Web 和唯一的
  `python -m app.douyin_daemon` 子进程；NAS 不再存在旧 `main.py` 运行模式。

两种 Docker 模式都由 `app.douyin_daemon` 持有 `ProcessManager`、错误分类和
`HealthState`。Web 只原子修改 YAML 并读取 `/data/state/health.json`，不会维护
第二套 FFmpeg 状态。daemon 监视 YAML 替换并原子切换不可变 `AppConfig` 快照；
停用或删除房间时由同一个 `ProcessManager` 收敛对应录制。

Linux 中 Launcher 子进程与 FFmpeg 使用独立进程组。停止时 Launcher 先拒绝 Web
写请求，再通知 daemon；daemon 停止新任务并按 SIGINT、terminate、kill 顺序收敛
FFmpeg，最后等待 Web 和录制线程退出。

## 持久化与安全

- daemon 配置位于 `/app/config/douyin.yaml`。
- 录制文件位于 `/data/downloads`，运行状态位于 `/data/state`。
- NAS Web 的日志目录为 `/app/logs`，配置只使用 `/app/config/douyin.yaml`。
- Cookie 优先通过 `/run/secrets/douyin_cookie` 注入。
- Web 管理端通过 `/run/secrets/web_token` 鉴权；管理页面与写请求要求认证，写请求
  还必须通过 CSRF 校验。未提供 Token 时禁止监听公网地址。
- 默认镜像发布到 `ghcr.io/gjjisadog/douyin-live-recorder`。

## 兼容性原则

- Docker 修复不得删除旧多平台 CLI。
- Windows GUI 不依赖 Docker target，不应在 Docker 回归修复中重构。
- 抖音 daemon 继续复用 `src` 中的解析能力，不在部署层修改解析算法。
