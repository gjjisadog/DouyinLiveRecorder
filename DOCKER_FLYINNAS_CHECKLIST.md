# 飞牛云一键部署清单

最后更新：2026-03-31

## 部署前

- 已安装飞牛云的 Docker / Compose 组件。
- 仓库文件已上传到飞牛云项目目录。
- 如需覆盖默认镜像标签或镜像仓库名，已按 [.env.docker.example](./.env.docker.example) 创建 `.env`。
- 已准备以下目录并确认有读写权限：
  - `config/`
  - `logs/`
  - `backup_config/`
  - `downloads/`
  - `client_data/docker-state/`
  - `client_data/secrets/`
- `config/douyin.yaml` 存在且可校验；允许先使用空 `rooms: []`，再从 Web 添加。
- `client_data/secrets/web_token` 至少包含 16 个随机字符。
- Cookie 如有需要，仅写入 `client_data/secrets/douyin_cookie`。

## 一键部署

1. 在飞牛云中进入项目目录。
2. 执行：

```bash
docker compose -f docker-compose.flyinnas.yaml up -d --build
```

3. 等待镜像构建和容器启动完成。
4. 执行：
```bash
python -m client.infra.docker.flyinnas_regression first-deploy --app-root .
```

## 部署后检查

- 执行 `docker compose -f docker-compose.flyinnas.yaml ps`，确认容器状态为 `Up`。
- 执行 `docker compose -f docker-compose.flyinnas.yaml logs -f`，确认没有 YAML
  校验、Secret 读取或模块导入错误。
- 执行 `docker inspect --format='{{json .State.Health}}' douyin-live-recorder`，确认健康检查状态为 `healthy`。
- 使用 Web Token 登录 `http://NAS_IP:18091`，添加一个房间并确认无需重启即可热加载。
- 确认 `downloads/` 目录能正常写入录制文件。
- 确认 `logs/` 目录持续输出运行日志。

## 常见回滚动作

- 停止容器：

```bash
docker compose -f docker-compose.flyinnas.yaml stop
```

- 重建容器：

```bash
docker compose -f docker-compose.flyinnas.yaml up -d --build
```

- 查看最近日志：

```bash
docker compose -f docker-compose.flyinnas.yaml logs --tail=200
```
