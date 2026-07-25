# 飞牛云运行回归清单

最后更新：2026-03-31

## 回归脚本

仓库内已提供可直接在飞牛云 / NAS 主机执行的回归脚本：

```bash
python -m client.infra.docker.flyinnas_regression first-deploy --app-root .
python -m client.infra.docker.flyinnas_regression upgrade-deploy --app-root . --expected-tag 4.0.7
python -m client.infra.docker.flyinnas_regression rollback-deploy --app-root . --expected-tag 4.0.7
```

说明：

- `--app-root` 指向飞牛云上的项目根目录，目录下需包含 Compose、`config/`、
  `logs/`、`backup_config/`、`downloads/`、`client_data/docker-state/` 和
  `client_data/secrets/`。
- `--expected-tag` 建议在升级部署和回滚部署时填写，用于校验当前容器实际运行的镜像标签。
- 如需给自动化平台消费结果，可追加 `--json` 输出 JSON 报告。

## 首次部署回归

### 部署前

- 已准备配置、日志、下载、状态和 Secret 挂载目录。
- `config/douyin.yaml` 合法；允许 `rooms: []`。
- `client_data/secrets/web_token` 已设置。
- 如需覆盖镜像名或标签，已按 [.env.docker.example](./.env.docker.example) 创建 `.env`。

### 执行

```bash
docker compose -f docker-compose.flyinnas.yaml up -d --build
python -m client.infra.docker.flyinnas_regression first-deploy --app-root .
```

### 回归点

- `docker compose -f docker-compose.flyinnas.yaml ps` 显示容器为 `Up`。
- `docker inspect --format='{{json .State.Health}}' douyin-live-recorder` 显示为 `healthy`。
- 日志中没有 YAML 校验、Secret、`ModuleNotFoundError` 或 FFmpeg 缺失错误。
- Web 需要 Token 和 CSRF，修改房间后 daemon 不重启即可更新 `configured_rooms`。
- `downloads/` 可正常创建录制输出目录或文件。
- `logs/` 持续写入运行日志。

## 升级部署回归

### 升级前

- 记录当前正在使用的镜像标签。
- 备份 `config/` 与关键历史日志。
- 确认新版本对应的 Compose / `.env` 已同步到飞牛云目录。

### 执行

```bash
docker compose -f docker-compose.flyinnas.yaml pull
docker compose -f docker-compose.flyinnas.yaml up -d --build
python -m client.infra.docker.flyinnas_regression upgrade-deploy --app-root . --expected-tag 4.0.7
```

### 回归点

- 容器能正常重建并恢复到 `healthy`。
- 现有 `config/douyin.yaml` 与两个 Secret 未被覆盖。
- `downloads/` 原有录制文件保持可读，新文件继续写入。
- `logs/` 中没有连续重启、健康检查失败或配置解析异常。
- 如有通知配置，至少验证一次状态通知仍可正常发送。

## 回滚部署回归

### 回滚前

- 明确要回滚到的镜像标签。
- 保留当前版本的 `config/`、`logs/` 和 Compose 文件快照。

### 执行

```bash
docker compose -f docker-compose.flyinnas.yaml down
```

将 `.env` 中的 `DLR_IMAGE_TAG` 改为目标旧版本后，再执行：

```bash
docker compose -f docker-compose.flyinnas.yaml up -d
python -m client.infra.docker.flyinnas_regression rollback-deploy --app-root . --expected-tag <目标旧版本>
```

### 回归点

- 容器可以用旧标签成功拉起。
- 健康检查恢复为 `healthy`。
- 回滚前应确认目标旧版本是否支持 `douyin.yaml`；不支持时需按该版本说明单独迁移，
  不要让当前 NAS 同时维护两套运行配置。
- 回滚后日志中没有持续的迁移失败、配置字段不兼容或重复重启问题。
- 如回滚目标需要继续录制，确认一条已有直播地址至少能进入正常监测状态。
