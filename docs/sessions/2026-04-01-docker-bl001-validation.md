# 2026-04-01 Docker BL-001 Validation

## 本次做了什么
- 从 `docs/handover/executable_backlog.md` 接手 `BL-001`“Docker 实机构建验收”。
- 核对了 `Dockerfile`、`docker-compose.flyinnas.yaml`、`client/infra/docker/healthcheck.py`、`client/infra/docker/flyinnas_regression.py`。
- 在当前 Windows 主机上确认 `Docker 29.3.1` 与 `Docker Compose v5.1.0` 可用。
- 为完成一次真实健康检查，临时把 README 里的公开示例地址 `https://live.douyin.com/745964462470` 写入 `config/URL_config.ini`。
- 首次执行 `docker compose -f docker-compose.flyinnas.yaml up -d --build` 时，遭遇 Debian 源瞬时 `502 Bad Gateway`。
- 为提升镜像构建稳定性，对 `Dockerfile` 加入显式 `apt` 重试循环后重新构建，第二次验收通过。
- 构建成功后补跑 `client.infra.docker.flyinnas_regression first-deploy --app-root .`，结果为 `PASS`。
- 验收完成后执行 `docker compose -f docker-compose.flyinnas.yaml down --remove-orphans`，并恢复原始 `config/URL_config.ini`。

## 关键命令
```powershell
docker --version
docker compose version
docker compose -f docker-compose.flyinnas.yaml down --remove-orphans
docker compose -f docker-compose.flyinnas.yaml up -d --build
docker compose -f docker-compose.flyinnas.yaml ps
docker inspect --format='{{json .State.Health}}' douyin-live-recorder
docker compose -f docker-compose.flyinnas.yaml logs --tail=200
& '.\.client-conda-env\python.exe' -m client.infra.docker.flyinnas_regression first-deploy --app-root .
docker compose -f docker-compose.flyinnas.yaml down --remove-orphans
```

## 已确认结果
- `docker --version` 输出：`Docker version 29.3.1, build c2be9cc`
- `docker compose version` 输出：`Docker Compose version v5.1.0`
- 镜像 `douyin-live-recorder:4.0.7` 构建成功
- 容器 `douyin-live-recorder` 状态为 `Up ... (healthy)`
- 健康检查输出：
  - `recorder healthy with 1 configured target(s)`
- 回归脚本输出：
  - `Result: PASS`
  - `container_state: state=running`
  - `container_health: health=healthy`
  - `container_image: image=douyin-live-recorder:4.0.7`

## 过程中的异常与处理
- 已确认异常：Debian 源瞬时 `502 Bad Gateway`
  - 触发点：镜像构建阶段 `apt-get install`
  - 处理：在 `Dockerfile` 中加入 shell 级重试循环，再次执行构建
  - 结果：重试版 Dockerfile 可完成本机构建
- 已确认现象：容器日志出现一次 `HTTP error occurred: 429 - Too Many Requests`
  - 背景：本次仅使用公开示例地址做健康检查与启动验证
  - 影响：不影响容器进程存活、健康检查或回归脚本结果

## 结论
- `BL-001` 在当前 Windows Docker 环境中已完成。
- 当前 Docker / NAS 线已经从“文档和脚本准备完成”推进到“本机真实构建、健康检查、回归脚本均已通过”。
- 下一步应转入：
  1. `BL-002` 客户端录制链路二轮人工冒烟
  2. `BL-004` 飞牛云 / NAS 主机实跑回归
