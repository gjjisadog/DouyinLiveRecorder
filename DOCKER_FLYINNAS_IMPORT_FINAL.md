# 飞牛 Docker UI 导入说明

最后更新：2026-07-25

## 使用的镜像

飞牛 NAS Web 模式使用：

```text
ghcr.io/gjjisadog/douyin-live-recorder:4.0.7-nas-web
```

该镜像来自 Dockerfile 的 `nas-web` target，入口固定为
`python -m client.infra.docker.launcher`。不要使用 daemon 标签替代。

## 导入前准备

创建以下目录，并准备 `config/douyin.yaml`：

```text
/vol1/docker/douyin-live-recorder/config/
/vol1/docker/douyin-live-recorder/logs/
/vol1/docker/douyin-live-recorder/backup_config/
/vol1/docker/douyin-live-recorder/downloads/
/vol1/docker/douyin-live-recorder/state/
```

如果存储卷不是 `/vol1`，请统一调整挂载源路径。

## 导入

将仓库中的 `docker-compose.flyinnas.import.yaml` 粘贴到飞牛 Docker UI。该文件：

- 不包含 `build:`。
- 固定使用 GHCR 的 `nas-web` 镜像标签。
- 将 18091 映射到 NAS。
- 将录制目录挂载到 `/data/downloads`，状态目录挂载到 `/data/state`。
- 使用 `client.infra.docker.healthcheck`。
- 设置 90 秒停止宽限期。

启动后访问：

```text
http://NAS_IP:18091
http://NAS_IP:18091/logs
```

## 停止检查

停止容器后确认：

1. 容器日志出现 `recorder stop stage=SIGINT`。
2. 子 daemon 输出 `daemon_stopped`。
3. 宿主机没有该容器遗留的 FFmpeg 进程。

Web 页仍保留旧 `URL_config.ini` 编辑能力；默认录制子进程已切换到
`app.douyin_daemon`，其实际录制配置来自 `config/douyin.yaml`。如需旧多平台入口，
显式设置 `DLR_RECORDER_MODE=legacy`。
