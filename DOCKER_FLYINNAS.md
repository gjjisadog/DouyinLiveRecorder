# 飞牛云 Docker 部署说明

最后更新：2026-03-31

## 适用说明

- 本说明面向飞牛云 / NAS 场景。
- 运行的是命令行录制版本，不是桌面客户端。
- 容器默认启用无交互模式：如果没有配置直播地址，不会卡在终端输入，而是直接输出错误并退出。
- Compose 默认会构建当前仓库代码，而不是拉取远端 `latest` 镜像。
- 当前默认镜像标签来自 `client/version.py`，在 Compose 中表现为 `${DLR_IMAGE_TAG:-4.0.7}`，避免部署时漂移到未知版本。

## 推荐目录

建议在飞牛云里给项目准备一个独立目录，例如：

```text
/vol1/docker/douyin-live-recorder
```

目录下至少保留这些挂载路径：

```text
config/
logs/
backup_config/
downloads/
```

## 首次准备

1. 将仓库文件放到飞牛云的项目目录中。
2. 编辑 `config/URL_config.ini`，一行一个直播间地址。
3. 按需编辑 `config/config.ini`。
4. 建议把录制格式设为 `ts`，这样容器异常退出时更不容易损坏文件。
5. 如需按单核对，可对照 [DOCKER_FLYINNAS_CHECKLIST.md](E:\Project\DouyinLiveRecorder-4.0.7\DOCKER_FLYINNAS_CHECKLIST.md) 完成部署前和部署后检查。
6. 如需按“首次部署 / 升级部署 / 回滚部署”分别回归，可对照 [DOCKER_FLYINNAS_REGRESSION.md](E:\Project\DouyinLiveRecorder-4.0.7\DOCKER_FLYINNAS_REGRESSION.md)。
7. 如需在飞牛云主机上直接执行回归校验，可运行：
```bash
python -m client.infra.docker.flyinnas_regression first-deploy --app-root .
```

## 启动方式

优先使用本仓库提供的飞牛云 Compose 文件：

```bash
docker compose -f docker-compose.flyinnas.yaml up -d --build
```

如果你的飞牛云界面只接受 Compose 内容，也可以直接导入 [docker-compose.flyinnas.yaml](E:\Project\DouyinLiveRecorder-4.0.7\docker-compose.flyinnas.yaml) 的内容。

如果你需要改成自己的镜像仓库名或自定义版本标签，可以在同目录下创建 `.env` 文件，参考 [.env.docker.example](E:\Project\DouyinLiveRecorder-4.0.7\.env.docker.example)。

容器构建完成后，会自动启用健康检查：

```bash
docker inspect --format='{{json .State.Health}}' douyin-live-recorder
```

如需在首次部署、升级部署或回滚部署后自动跑一轮回归，可直接执行：

```bash
python -m client.infra.docker.flyinnas_regression first-deploy --app-root .
```

## SSH 一键部署

如果你的电脑可以通过 SSH 直连飞牛 NAS，现在可以直接从本机一键上传、部署并触发回归。

Windows PowerShell：

```powershell
.\deploy_flyinnas.ps1 `
  -RemoteHost 192.168.1.20 `
  -User admin `
  -Scenario first-deploy
```

Linux / macOS / Git Bash：

```bash
./deploy_flyinnas.sh \
  --host 192.168.1.20 \
  --user admin \
  --scenario first-deploy
```

常用参数：

- `--remote-dir` / `-RemoteDir`：飞牛 NAS 上的项目目录，默认 `/vol1/docker/douyin-live-recorder`
- `--scenario` / `-Scenario`：`first-deploy`、`upgrade-deploy`、`rollback-deploy`
- `--expected-tag` / `-ExpectedTag`：期望部署后的镜像标签；回滚时改成目标旧版本
- `--identity-file` / `-IdentityFile`：SSH 私钥路径
- `--remote-python` / `-RemotePython`：NAS 上用于执行回归脚本的 Python，默认 `python3`
- `--dry-run` / `-DryRun`：只打印实际将要执行的 `scp` / `ssh` 命令，不真正执行

说明：

- 脚本会自动打包当前仓库代码并上传到 NAS。
- 会自动避开本地 `.client-conda-env`、`build/`、`dist/`、`logs/`、`downloads/`、`backup_config/`、`client_data/` 等大目录和运行目录。
- 远端已有的 `config/config.ini` 与 `config/URL_config.ini` 默认不会被覆盖；仅在首次不存在时才从仓库模板补齐。
- 上传完成后会执行 `docker compose -f docker-compose.flyinnas.yaml up -d --build`，并自动调用 `python -m client.infra.docker.flyinnas_regression ...` 做回归。

## 停止与查看

停止：

```bash
docker compose -f docker-compose.flyinnas.yaml stop
```

查看日志：

```bash
docker compose -f docker-compose.flyinnas.yaml logs -f
```

## 关键行为

- 容器内默认设置了 `DLR_HEADLESS=1`。
- 当 `config/URL_config.ini` 为空时，程序会输出明确错误并退出，避免在 NAS 中卡死在 `input()`。
- `docker-compose.flyinnas.yaml` 使用 `restart: unless-stopped`，适合长期开机运行。
- 健康检查会同时确认 `config/URL_config.ini` 非空，且容器内 `python main.py` 主进程仍在运行。

## 常见问题

### 容器一启动就退出

优先检查：

- `config/URL_config.ini` 是否已经写入直播地址
- `config/config.ini` 是否存在并可读
- 挂载目录是否正确
- `docker inspect --format='{{json .State.Health}}' douyin-live-recorder` 是否显示为 `unhealthy`

### 为什么不建议跑桌面客户端

飞牛云上的 Docker 更适合运行当前仓库的命令行录制主程序；桌面客户端依赖 GUI，不适合 NAS 容器环境。
