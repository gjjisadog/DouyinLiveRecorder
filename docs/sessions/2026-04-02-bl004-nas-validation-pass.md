# 2026-04-02 BL-004 NAS 实机验收通过

## 本次做了什么
- 在真实 NAS `192.168.5.41` / `admin` 上完成了 `BL-004` 的 SSH、Docker 权限、容器启动与三段回归验证。
- 修复了 `client/infra/docker/flyinnas_deploy.py` 在 Windows 上通过 SSH stdin 传 shell 脚本时的 CRLF 问题。
- 尝试过两条真实部署路径：
  1. 远端 `docker compose up -d --build`
  2. 本地已有镜像 `docker save` -> 传输到 NAS -> `docker load` -> 远端 `docker compose up -d`
- 最终第 2 条路径在真实 NAS 上成功完成了本轮验收。

## 已确认
- SSH 已打通，且 `admin` 已加入 `docker` 组。
- 远端环境：
  - `docker --version` = `28.5.2`
  - `docker compose version` = `v2.40.3`
  - `python3 --version` = `3.11.2`
- 真实 NAS 上容器已启动并健康：
  - 容器名：`douyin-live-recorder`
  - 镜像：`douyin-live-recorder:4.0.7`
  - 状态：`Up ... (healthy)`
- 健康检查返回：
  - `recorder healthy with 1 configured target(s)`
- 日志已确认程序启动并输出版本、平台列表、`ffmpeg version` 与“系统代理检测中，请耐心等待...”。

## 回归结果
- `python3 -m client.infra.docker.flyinnas_regression first-deploy --app-root .`
  - `PASS`
- `python3 -m client.infra.docker.flyinnas_regression upgrade-deploy --app-root . --expected-tag 4.0.7`
  - `PASS`
- `python3 -m client.infra.docker.flyinnas_regression rollback-deploy --app-root . --expected-tag 4.0.7`
  - `PASS`

## 本次验收采用的实际落地路径
- 由于 NAS 直构时网络过慢/不稳定，远端 `docker build` 在安装 `ffmpeg` 或下载静态包时都出现过超时/SSL EOF。
- 本机此前已有可用的 `linux/amd64` 镜像：
  - `douyin-live-recorder:4.0.7`
  - `sha256:3ca7ddc9cf1d17f45cce3db605350717e2dc16870432ed1538ae67760cdefee5`
- 因此本轮实机验收改为：
  1. `docker save -o tmp_douyin_live_recorder_4.0.7.tar douyin-live-recorder:4.0.7`
  2. `scp` 上传到 NAS
  3. `docker load -i ...`
  4. `docker compose -f docker-compose.flyinnas.yaml up -d`
  5. 运行三段回归脚本

## 推断
- `BL-004` 从“真实 NAS 能否运行当前 Docker 方案”的角度看，已经完成闭环。
- 但如果把“必须由 NAS 自己从源码稳定完成 `docker compose up -d --build`”也算作通过标准，则远端直构链路仍有网络层不稳定因素，需要单独继续优化。

## 待确认
- 是否要继续把 NAS 直构优化到稳定可复现，而不是依赖“本地构建 + 镜像传输”。
- 当前写入 NAS 的 `config/URL_config.ini` 为验收用公开示例地址，后续是否替换为真实地址或恢复为空模板。
