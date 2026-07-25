# 飞牛云 Docker 部署说明

最后更新：2026-04-10

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
5. 如需按单核对，可对照 [DOCKER_FLYINNAS_CHECKLIST.md](./DOCKER_FLYINNAS_CHECKLIST.md) 完成部署前和部署后检查。
6. 如需按“首次部署 / 升级部署 / 回滚部署”分别回归，可对照 [DOCKER_FLYINNAS_REGRESSION.md](./DOCKER_FLYINNAS_REGRESSION.md)。
7. 如需在飞牛云主机上直接执行回归校验，可运行：
```bash
python -m client.infra.docker.flyinnas_regression first-deploy --app-root .
```

## 启动方式

优先使用本仓库提供的飞牛云 Compose 文件：

```bash
docker compose -f docker-compose.flyinnas.yaml up -d --build
```

启动完成后，可直接在浏览器访问 `http://NAS_IP:18091` 打开 Docker 管理页：

- `/`：主播配置页，可增删或停用主播配置
- `/logs`：日志控制台，可查看当前录制日志

页面保存的内容会写入挂载目录下的 `config/URL_config.ini`；日志控制台读取
`logs/`。默认 daemon 子进程实际使用 `config/douyin.yaml`，旧 URL 配置页主要
用于显式 `DLR_RECORDER_MODE=legacy` 的多平台兼容模式。

如果你准备走“飞牛 Docker UI 导入 Compose + 固定镜像标签”的方式，仓库里额外提供了 [docker-compose.flyinnas.import.yaml](./docker-compose.flyinnas.import.yaml)：

- 不依赖 `build:`
- 使用固定镜像标签 `ghcr.io/gjjisadog/douyin-live-recorder:4.0.7-nas-web`
- 使用固定端口映射 `18091:18091`
- 使用绝对挂载路径 `/vol1/docker/douyin-live-recorder/...`

这份文件更适合直接粘贴到飞牛 Docker UI 的 Compose 导入页，减少变量替换和本地构建对面板识别的干扰。

如果你的飞牛云界面只接受 Compose 内容，也可以直接导入 [docker-compose.flyinnas.yaml](./docker-compose.flyinnas.yaml) 的内容。

如果你需要改成自己的镜像仓库名或自定义版本标签，可以在同目录下创建 `.env` 文件，参考 [.env.docker.example](./.env.docker.example)。
如果 `18091` 端口冲突，也可以在 `.env` 中覆写 `DLR_WEB_PORT`。

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

查看容器总日志：

```bash
docker compose -f docker-compose.flyinnas.yaml logs -f
```

如果只想确认配置页是否正常，可访问：
```bash
curl http://127.0.0.1:18091/health
```

如果希望直接看录制器文件日志，优先打开：

```text
http://NAS_IP:18091/logs
```

该页面默认提供：

- `streamget.log`
- `PlayURL.log`

## 固定镜像

优先直接从 GHCR 拉取 `ghcr.io/gjjisadog/douyin-live-recorder:4.0.7-nas-web`。
离线环境可先导出该镜像：

```bash
docker save ghcr.io/gjjisadog/douyin-live-recorder:4.0.7-nas-web -o douyin-live-recorder-4.0.7-nas-web.tar
```

将 tar 包导入 NAS 后，再用 [docker-compose.flyinnas.import.yaml](./docker-compose.flyinnas.import.yaml) 创建容器。

## 关键行为

- 容器内默认设置 `DLR_HEADLESS=1` 和 `DLR_RECORDER_MODE=daemon`。
- `nas-web` 入口是 `python -m client.infra.docker.launcher`，Launcher 默认拉起
  `python -m app.douyin_daemon`；旧 `main.py` 仅作为显式 legacy 兼容入口保留。
- Docker 网页入口现在同时提供主播配置页和只读日志控制台，更适合 NAS / FN Connect 场景。
- `docker-compose.flyinnas.yaml` 使用 `restart: unless-stopped`，适合长期开机运行。
- 健康检查同时确认 Launcher、Web `/health`、daemon 进程和 daemon 健康状态。
- 停止宽限期为 90 秒；Launcher 按 SIGINT、terminate、kill 顺序停止独立进程组。

## 常见问题

### 容器一启动就退出

优先检查：

- `config/URL_config.ini` 是否已经写入直播地址
- `config/config.ini` 是否存在并可读
- 挂载目录是否正确
- `docker inspect --format='{{json .State.Health}}' douyin-live-recorder` 是否显示为 `unhealthy`

### 为什么不建议跑桌面客户端

飞牛云上的 Docker 更适合运行当前仓库的命令行录制主程序；桌面客户端依赖 GUI，不适合 NAS 容器环境。
