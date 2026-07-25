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

创建以下目录，并准备 `config/douyin.yaml`、Web Token 和可选 Cookie Secret：

```text
/vol1/docker/douyin-live-recorder/config/
/vol1/docker/douyin-live-recorder/logs/
/vol1/docker/douyin-live-recorder/backup_config/
/vol1/docker/douyin-live-recorder/downloads/
/vol1/docker/douyin-live-recorder/state/
/vol1/docker/douyin-live-recorder/secrets/
/vol1/docker/douyin-live-recorder/secrets/web_token
/vol1/docker/douyin-live-recorder/secrets/douyin_cookie
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

浏览器认证时用户名可任意填写，密码为 `secrets/web_token` 的内容。所有管理页面
和写操作都要求认证，写操作同时要求页面签发的 CSRF Token。

## 停止检查

停止容器后确认：

1. 容器日志出现 `recorder stop stage=SIGINT`。
2. 子 daemon 输出 `daemon_stopped`。
3. 宿主机没有该容器遗留的 FFmpeg 进程。

Web 与录制子进程只使用 `config/douyin.yaml`。Launcher 固定启动
`python -m app.douyin_daemon`，NAS 模式不再提供 `main.py` 或 `URL_config.ini`
兼容开关；旧多平台源码入口仍保留在仓库中供非 NAS 场景使用。
