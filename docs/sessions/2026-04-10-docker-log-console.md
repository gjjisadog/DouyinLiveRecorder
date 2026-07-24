# 2026-04-10 Docker 日志控制台

## 背景
- 用户希望通过飞牛 NAS 的 `FN Connect` / 容器网页入口直接查看录制运行日志。
- 当前项目更适合提供稳定的只读日志控制台，而不是在容器里暴露 shell 终端。

## 调整
- 扩展 `client.infra.docker.config_web`
  - 保留原有主播配置页 `/`
  - 新增日志控制台 `/logs`
  - 页面内增加顶部导航，在“主播配置”和“日志控制台”之间切换
- 新增日志读取封装 `DockerLogStore`
  - 固定只读取 `/app/logs`
  - 目前支持 `streamget.log` 与 `PlayURL.log`
  - 仅提供只读尾部查看，不提供写入或 shell 能力
- 日志控制台支持
  - 切换日志文件
  - 选择显示行数
  - 刷新查看最新日志

## 验证
- 语法校验：
  - `& '.\.client-conda-env\python.exe' -m py_compile client\infra\docker\config_web.py`
- 单测：
  - `& '.\.client-conda-env\python.exe' -m unittest client.tests.test_docker_config_web -v`
  - `& '.\.client-conda-env\python.exe' -m unittest client.tests.test_docker_healthcheck -v`

## 结论
- NAS 上的单一 Web 入口现在同时覆盖：
  - 主播配置管理
  - 录制日志查看
- 对当前录播项目而言，这种“配置页 + 只读日志控制台”的方式比在容器里开放 shell 更稳，也更容易被飞牛面板识别为可访问网页。
