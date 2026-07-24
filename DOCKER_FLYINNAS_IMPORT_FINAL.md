# 飞牛 Docker UI 导入最终说明

最后更新：2026-04-10

## 用途

这份说明用于飞牛 NAS 的 Docker UI 场景：

- 先导入镜像 tar 包
- 再把下面的 Compose 直接粘贴到飞牛 Docker UI 的 Compose 导入页
- 容器启动后即可通过 Web 管理页管理主播列表并查看录制日志

对应镜像 tar：

- `douyin-live-recorder-4.0.7-fnos-webui.tar`

对应镜像标签：

- `douyin-live-recorder:4.0.7-fnos-webui`

## 导入前准备

先在飞牛 NAS 上创建目录：

```text
/vol1/docker/douyin-live-recorder/
/vol1/docker/douyin-live-recorder/config/
/vol1/docker/douyin-live-recorder/logs/
/vol1/docker/douyin-live-recorder/backup_config/
/vol1/docker/douyin-live-recorder/downloads/
```

如果你的飞牛存储卷不是 `/vol1`，把下面 Compose 里的路径统一替换成你的实际路径。

## 飞牛 UI 可直接粘贴的 Compose

```yaml
services:
  douyin-live-recorder:
    image: douyin-live-recorder:4.0.7-fnos-webui
    container_name: douyin-live-recorder
    environment:
      TZ: Asia/Shanghai
      TERM: xterm-256color
      DLR_HEADLESS: "1"
      DLR_WEB_HOST: 0.0.0.0
      DLR_WEB_PORT: "18091"
    volumes:
      - /vol1/docker/douyin-live-recorder/config:/app/config
      - /vol1/docker/douyin-live-recorder/logs:/app/logs
      - /vol1/docker/douyin-live-recorder/backup_config:/app/backup_config
      - /vol1/docker/douyin-live-recorder/downloads:/app/downloads
    ports:
      - "18091:18091"
    healthcheck:
      test: ["CMD", "python", "-m", "client.infra.docker.healthcheck"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    stop_grace_period: 30s
```

## 导入步骤

1. 在飞牛 Docker UI 里导入镜像 `douyin-live-recorder-4.0.7-fnos-webui.tar`
2. 确认镜像标签显示为 `douyin-live-recorder:4.0.7-fnos-webui`
3. 打开 Compose 导入
4. 直接粘贴上面的 Compose
5. 点击创建 / 启动

## 启动后访问

容器启动后访问：

```text
http://NAS_IP:18091
```

首页访问地址：

```text
http://NAS_IP:18091
```

日志控制台地址：

```text
http://NAS_IP:18091/logs
```

其中首页可以：

- 新增主播直播间
- 启用 / 停用主播
- 删除主播
- 批量编辑 `URL_config.ini`

日志控制台可以：

- 查看 `streamget.log`
- 查看 `PlayURL.log`
- 按 100 / 200 / 500 / 1000 行刷新查看最新日志

## 当前行为说明

- 即使还没有添加任何主播，容器也会保持 `Up`，不会反复重启
- 没有主播时，健康检查会显示“waiting for configuration”
- 一旦你在网页里添加了主播，录制主进程会自动拉起

## 建议

- 如果飞牛面板没有立刻显示“链接图标”，先刷新容器列表
- 确保容器状态为 `运行中`
- 确保端口映射显示为 `18091:18091`
- 确保浏览器能直接打开 `http://NAS_IP:18091`
