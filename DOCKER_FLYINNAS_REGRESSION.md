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

- `--app-root` 指向飞牛云上的项目根目录，目录下需包含 `docker-compose.flyinnas.yaml`、`config/`、`logs/`、`backup_config/`、`downloads/`。
- `--expected-tag` 建议在升级部署和回滚部署时填写，用于校验当前容器实际运行的镜像标签。
- 如需给自动化平台消费结果，可追加 `--json` 输出 JSON 报告。

## 首次部署回归

### 部署前

- 已准备 `config/`、`logs/`、`backup_config/`、`downloads/` 四个挂载目录。
- `config/URL_config.ini` 已写入至少一个直播间地址。
- 如需覆盖镜像名或标签，已按 [.env.docker.example](E:\Project\DouyinLiveRecorder-4.0.7\.env.docker.example) 创建 `.env`。

### 执行

```bash
docker compose -f docker-compose.flyinnas.yaml up -d --build
python -m client.infra.docker.flyinnas_regression first-deploy --app-root .
```

### 回归点

- `docker compose -f docker-compose.flyinnas.yaml ps` 显示容器为 `Up`。
- `docker inspect --format='{{json .State.Health}}' douyin-live-recorder` 显示为 `healthy`。
- `docker compose -f docker-compose.flyinnas.yaml logs --tail=200` 中没有 `URL_config.ini 为空`、`ModuleNotFoundError`、`ffmpeg` 缺失等启动错误。
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
- 旧的 `config/config.ini` 与 `config/URL_config.ini` 未被覆盖。
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
- 旧版本能够继续读取现有 `config/URL_config.ini` 与 `config/config.ini`。
- 回滚后日志中没有持续的迁移失败、配置字段不兼容或重复重启问题。
- 如回滚目标需要继续录制，确认一条已有直播地址至少能进入正常监测状态。
