# 2026-04-05 Docker 配置页

## 背景
- 用户希望 Docker 部署不再只靠手工编辑 `config/URL_config.ini`，而是提供一个容器内可访问的配置网页，用来添加和管理要录制的主播。

## 目标
- 保持现有 CLI 录制主流程 `main.py` 不变。
- 在 Docker / NAS 场景下提供一个轻量 Web 配置页。
- 页面直接读写挂载出来的 `config/URL_config.ini`。
- 配置保存后无需重启录制主程序即可在后续轮询中生效。

## 实现
- 新增 `client/infra/docker/config_web.py`
  - 基于标准库 `http.server`
  - 支持查看当前主播配置
  - 支持新增主播
  - 支持启用 / 停用 / 删除单条配置
  - 支持批量编辑 `URL_config.ini` 原始内容
  - 提供 `/health` 端点
- 新增 `client/infra/docker/launcher.py`
  - 作为 Docker 新入口
  - 先启动配置页，再拉起 `python main.py`
  - 转发退出信号，保证容器停止时能正确结束子进程
- 更新 `Dockerfile`
  - `CMD ["python", "-m", "client.infra.docker.launcher"]`
- 更新 `docker-compose.yaml` 与 `docker-compose.flyinnas.yaml`
  - 新增 `DLR_WEB_HOST`
  - 新增 `DLR_WEB_PORT`
  - 新增网页端口映射
- 更新 `.env.docker.example`
  - 增加 `DLR_WEB_PORT=18091`

## 测试
- 新增 `client/tests/test_docker_config_web.py`
  - 验证配置存储增删改
  - 验证 HTTP 页面可访问并能新增主播
- 扩展 `client/tests/test_docker_release.py`
  - 验证 Compose 和 `.env.docker.example` 已包含 `DLR_WEB_PORT`
- 执行：
  - `& '.\.client-conda-env\python.exe' -m unittest client.tests.test_docker_config_web client.tests.test_docker_healthcheck client.tests.test_docker_release client.tests.test_flyinnas_deploy -v`
  - `& '.\.client-conda-env\python.exe' -m py_compile client\infra\docker\config_web.py client\infra\docker\launcher.py client\tests\test_docker_config_web.py`

## 使用说明
- 默认地址：`http://localhost:18091`
- NAS 场景：`http://NAS_IP:18091`
- 如端口冲突，可在 `.env` 中设置 `DLR_WEB_PORT`

## 风险与边界
- 当前配置页默认无鉴权，适合局域网或受控网络环境。
- 页面只管理 `config/URL_config.ini`，不处理 `config/config.ini` 中的敏感配置。
