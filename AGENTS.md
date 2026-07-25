# AGENTS.md

## 项目定位

- 本仓库是 Python 直播录制项目，同时保留旧多平台 CLI、PySide6 Windows 客户端和 Docker/NAS 运行模式。
- `main.py` 与 `src/` 是旧多平台入口；不得因 Docker 修复而删除或改写其平台解析能力。
- `app/` 是抖音无头 daemon；`client/infra/docker/` 提供 NAS Web 启动器、健康检查和部署工具。

## 目录边界

- `main.py`、`src/`、`msg_push.py`、`ffmpeg_install.py`：旧多平台录制链路。
- `app/`：Linux/NAS 无人值守抖音 daemon、健康状态和 FFmpeg 进程管理。
- `client/`：Windows GUI 及共享服务；Docker 适配位于 `client/infra/docker/`。
- `config/`、`logs/`、`client_data/`：运行配置、日志和状态。
- `Dockerfile`、`docker-compose*.yaml`、`build_docker_release.*`：Docker 构建与发布。
- `docs/handover/`、`docs/architecture/`、`docs/sessions/`：长期交接资料。

## Docker 运行契约

- `daemon` target：`python -m app.douyin_daemon`，健康检查为 `python -m app.health check`，不暴露 Web 端口。
- `nas-web` target：`python -m client.infra.docker.launcher`，健康检查为 `python -m client.infra.docker.healthcheck`，Web 端口默认 18091。
- Compose 必须显式选择 target，不依赖 Dockerfile 最后一个阶段的默认 CMD。
- Linux 子进程必须使用独立进程组；停止顺序为 SIGINT、等待、terminate、等待、kill。
- 所有 Compose 的 `stop_grace_period` 不得低于 90 秒。

## 常用验证

- 全量测试：`python -m pytest -v`
- 编译检查：`python -m compileall -q app client tests scripts main.py`
- Compose：
  - `docker compose -f docker-compose.yaml config`
  - `docker compose -f docker-compose.flyinnas.yaml config`
  - `docker compose -f docker-compose.flyinnas.import.yaml config`
- 镜像：
  - `docker build --target daemon -t dlr-daemon:test .`
  - `docker build --target nas-web -t dlr-nas-web:test .`
- 运行时烟雾：`python scripts/docker_runtime_smoke.py --daemon-image dlr-daemon:test --nas-image dlr-nas-web:test`

## 文档与编码

- 文本文件使用 UTF-8、LF，并保留文件末尾换行。
- 文档和配置不得记录开发者本机绝对路径、Cookie、令牌或其他秘密。
- 完成重要阶段时同步：
  - `docs/handover/current_status.md`
  - `docs/handover/next_steps.md`
  - `docs/handover/known_issues.md`
  - `docs/sessions/YYYY-MM-DD-<topic>.md`
- 缺失证据必须明确标记为“未知”“待验证”或“未执行”，不得补造历史结论。
