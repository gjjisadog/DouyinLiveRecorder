# 下一步

最后更新：2026-07-25

## Docker 合并回归后续

1. 在功能分支 CI 上确认 GHCR 双 target 矩阵发布元数据和 Trivy SARIF 上传。
2. 在真实飞牛 NAS 上复核 `nas-web` 的目录权限、90 秒停止宽限期和 legacy
   多平台兼容模式；本阶段只完成本机 Docker Desktop 的真实容器验收。
3. Draft PR #1 已被 `main` 取代，建议维护者关闭并在关闭原因中引用当前主线。
4. Web 页仍编辑旧 `URL_config.ini`，而默认 daemon 使用 `douyin.yaml`；在不新增
   Web 功能的前提下，本阶段仅通过文档明确边界。后续若统一配置模型，应单独立项。

## Docker 配置页
1. 如需继续增强 Docker 管理能力，优先在现有 `client.infra.docker.config_web` 上迭代。
   - 当前已支持新增、停用、删除、批量编辑 `URL_config.ini`
   - 当前已支持只读日志控制台 `/logs`
   - 后续可考虑补充简单鉴权或把 `config/config.ini` 做页面化
2. 如果新增 Docker / NAS 功能，优先保持 `main.py` 录制链路不变，通过旁路服务或启动器扩展，避免把 Web 管理逻辑直接耦合进录制主循环。
3. 如需继续优化飞牛面板中的“快捷访问”显示，优先沿 `docker-compose.flyinnas.import.yaml` 保持：
   - 固定镜像标签
   - 固定宿主机端口
   - 绝对挂载路径
   - 容器健康且空配置时仍保持常驻

## P2
1. 如需继续补强发布背书，可补“第二条外部长时真实 `1 GB` 全量样本”
   - 当前已有证据：本地连续流真实 `1 GB` 样本 + Global News 外部长时真实 `1 GB` 样本
   - 当前已探索的第二外部源：`23 ABC / Uplynk`
   - 若继续沿 `23 ABC / Uplynk` 走，需要比当前 `5100s` 更长的录制窗口
   - 若当前目标只是可提交/可发布，这项可以不做
2. 如需继续增强文件桥，优先沿当前桥接方案扩展
   - 不建议回退到外部 UIAutomation / `pywinauto` 点击方案

## 抖音 Docker daemon 后续

1. 完成已启动的真实 NAS 24 小时观察，汇总健康、录制、Cookie/风控分类计数；
   当前隔离配置共 3 个房间，其中 2 个公开测试房间正在以 SD 画质录制；
   多房间完整 24 小时检查点为 2026-07-26 09:48（Asia/Shanghai）。
2. 在真实 ARMv7 NAS/开发板上补做录制与优雅停止后，再决定是否把实验目标纳入
   正式多架构发布；当前只完成 buildx/QEMU 运行验证。
3. 观察 NAS 的 remux CPU/IO 后，再决定是否将 `remux_workers` 上调到 2；默认保持关闭。
