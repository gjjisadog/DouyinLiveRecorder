# 2026-04-08 飞牛导入镜像

## 背景
- 用户希望两件事同时成立：
  - 当前 Docker 行为彻底固化为一个可复用镜像，避免以后重建又回退到旧逻辑
  - 额外提供一份更适合飞牛 Docker UI 导入的 Compose 文件，尽量提高 NAS 面板识别 Web 配置页入口的概率

## 调整
- 优化 `Dockerfile`
  - 改为先复制 `requirements.docker.txt`
  - 先安装系统依赖、Node.js、pip 依赖、ffmpeg
  - 最后再复制仓库代码
  - 目标是让后续源码改动不必反复重跑依赖安装层
- 新增 `docker-compose.flyinnas.import.yaml`
  - 使用固定镜像标签 `douyin-live-recorder:4.0.7-fnos-webui`
  - 不包含 `build:`
  - 使用固定端口 `18091:18091`
  - 使用飞牛常见绝对路径 `/vol1/docker/douyin-live-recorder/...`
- 更新文档
  - `DOCKER_FLYINNAS.md`
  - `docs/handover/current_status.md`
  - `docs/handover/next_steps.md`
  - `docs/handover/known_issues.md`

## 构建与验证
- 单测：
  - `& '.\.client-conda-env\python.exe' -m unittest client.tests.test_docker_release client.tests.test_docker_healthcheck -v`
- 语法校验：
  - `& '.\.client-conda-env\python.exe' -m py_compile client\infra\docker\launcher.py client\infra\docker\healthcheck.py`
- 固定镜像构建成功：
  - `docker build -t douyin-live-recorder:4.0.7-fnos-webui .`
- 冒烟验证：
  - 使用临时容器映射 `18092 -> 18091`
  - 空 `URL_config.ini` 下容器保持 `Up (healthy)`
  - `http://127.0.0.1:18092/health` 返回 `200 ok`

## 结论
- 当前仓库已经具备两个 Docker 入口：
  - 常规源码构建：`docker-compose.flyinnas.yaml`
  - 飞牛 UI 导入优先：`docker-compose.flyinnas.import.yaml`
- 已固化的镜像标签是 `douyin-live-recorder:4.0.7-fnos-webui`
- 对飞牛面板“链接图标”的策略仍以兼容性优先：
  - 稳定运行的容器
  - 固定端口
  - 健康检查通过
  - 空配置时 Web 配置页也常驻
