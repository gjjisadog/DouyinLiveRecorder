# 架构概览

最后更新：2026-07-25

## 运行入口

| 模式 | 入口 | 主要配置 | 输出与状态 |
| --- | --- | --- | --- |
| 旧多平台 CLI | `python main.py` | `config/config.ini`、`config/URL_config.ini` | `downloads/`、`logs/` |
| Windows 客户端 | `python client/main.py` | `client_data/` 与兼容 INI | GUI、历史数据库、录制文件 |
| Docker daemon | `python -m app.douyin_daemon` | `config/douyin.yaml`、Cookie Secret | `/data/downloads`、`/data/state` |
| 飞牛 NAS Web | `python -m client.infra.docker.launcher` | daemon YAML；legacy 模式使用旧 INI | Web 18091、录制与状态挂载 |

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
- `nas-web`：启动 Docker Launcher，Launcher 默认拉起新 daemon；显式 `DLR_RECORDER_MODE=legacy` 时仍可运行旧 `main.py`。

两种模式都以非 root 用户运行。Linux 中 Launcher 子进程与 FFmpeg 使用独立进程组，以便在容器停止时按 SIGINT、terminate、kill 顺序收敛。

## 持久化与安全

- daemon 配置位于 `/app/config/douyin.yaml`。
- 录制文件位于 `/data/downloads`，运行状态位于 `/data/state`。
- NAS Web 的日志目录为 `/app/logs`，旧 URL 配置页仍使用 `/app/config/URL_config.ini`。
- Cookie 优先通过 `/run/secrets/douyin_cookie` 注入。
- 默认镜像发布到 `ghcr.io/gjjisadog/douyin-live-recorder`。

## 兼容性原则

- Docker 修复不得删除旧多平台 CLI。
- Windows GUI 不依赖 Docker target，不应在 Docker 回归修复中重构。
- 抖音 daemon 继续复用 `src` 中的解析能力，不在部署层修改解析算法。
