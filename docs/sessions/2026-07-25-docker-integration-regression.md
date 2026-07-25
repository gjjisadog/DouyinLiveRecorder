# 2026-07-25 Docker 合并回归第一阶段

## 范围

- 修复 daemon 与飞牛 NAS Web 合并后的 Docker 入口、健康检查和停止流程。
- 修复 CI 覆盖、GHCR 发布归属、UTF-8 文档与本机路径问题。
- 不修改 Windows GUI、不修改抖音解析算法、不删除旧多平台入口。

## 主要修改

- Dockerfile 拆为 `daemon` 与 `nas-web` target。
- 三份 Compose 显式绑定 target、挂载路径、Healthcheck 和 90 秒停止宽限期。
- Launcher 默认启动 `app.douyin_daemon`，保留显式 legacy 模式。
- Launcher 和 `ProcessManager` 使用 Linux 独立进程组，并按 SIGINT、terminate、
  kill 顺序停止。
- 旧 `main.py` 的 SIGTERM 处理改为同样停止已登记的 FFmpeg 进程组。
- FlyInNAS 部署包新增 `douyin.yaml` 与状态目录。
- CI 改为全量测试、三份 Compose、双 target 构建和真实容器运行时烟雾。
- 发布目标改为 `ghcr.io/gjjisadog/douyin-live-recorder`，使用 `GITHUB_TOKEN`。
- 新增 `.editorconfig` 和 UTF-8/明显乱码/本机路径检查。

## 验证

- `python -m pytest -v`：148 项通过。
- 三份 `docker compose ... config`：通过。
- `docker build --target daemon -t dlr-daemon:test .`：通过。
- `docker build --target nas-web -t dlr-nas-web:test .`：通过。
- `scripts/docker_runtime_smoke.py`：通过。
  - 两种镜像 CMD 与 Healthcheck 元数据正确。
  - daemon 没有无关端口。
  - NAS Web 随机宿主机端口可访问。
  - `docker stop --time 90` 触发 SIGINT 优雅停止。
  - 停止后的 FFmpeg fixture 容器不再运行。
  - 生成的 TS 通过容器内 `ffprobe`。
- UTF-8 检查：228 个已跟踪文本文件通过。

## PR 状态

Draft PR #1 仍为 open draft，base 为 `legacy-4.0.7-base`。其 head `5e2d4d4`
已经是当前 `main` 的祖先，因此该 PR 已被主线取代（superseded），建议关闭。
本阶段未直接修改或关闭该 PR。

## 未执行与风险

- 未执行 24/72 小时测试。
- 未在真实飞牛 NAS 上执行本次镜像。
- 未触发本分支 GitHub Actions，因此 GHCR 推送和 SARIF 上传仍待线上验证。
- NAS Web 页与 daemon YAML 仍是两个配置界面；本阶段只明确边界，没有新增 Web 功能。
