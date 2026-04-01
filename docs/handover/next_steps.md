# 下一步

最后更新：2026-04-02

## 优先级 P0
1. 在真实 NAS / 飞牛云宿主机完成 `BL-004`
   - 已确认：Windows 本机已完成单测、部署 dry-run、容器健康检查与 `first-deploy` / `upgrade-deploy` / `rollback-deploy` 三种回归。
   - 待确认：飞牛云 / NAS 宿主机的挂载路径、宿主机权限、网络稳定性，以及真实 SSH 部署结果。
2. 若短期内拿不到 NAS 宿主机，切到 `BL-008` Git 状态基线恢复
   - 已确认：`BL-007` 已完成，`tmp*/` 忽略规则与清理脚本已落地；`BL-008` 也已完成目录分类与 ignore 收敛。
   - 待确认：是否直接在当前仓库建立“首个恢复提交基线”，以及如何处理无权限孤儿目录。

## 优先级 P1
3. 如需继续补客户端平台证据，追加“虎牙 / 斗鱼 / YY / B站”专项回归
   - 已确认：这些平台已存在于 `client/core/platform_router.py` 与 `client/core/stream_resolver.py`。
   - 待确认：当前代码基线下，它们的客户端解析分支是否已真实可用并拥有自动化证据。
4. 如需发布前补人工确认，收尾 `BL-002` 的 GUI 手点验收
   - 已确认：源码入口与 `dist` 包装版入口都能启动；真实录制链路已在临时工作区跑通。
   - 待确认：GUI 手工点击“新增任务 / 行内按钮 / 右键菜单 / 日志页 / 历史页”是否完全符合预期。
5. 如需进一步固化配置安全边界，考虑补充示例同步规则
   - 已确认：当前已存在 `config/config.example.ini` 与 `config/URL_config.example.ini`
   - 待确认：后续是否需要脚本化校验“示例文件字段不落后于真实配置”
6. 如需继续恢复发布链路，可补外部证据对照
   - 已确认：仓库内已经能恢复当前版本号、打包脚本、产物命名和当前 manifest / sha256
   - 待确认：历史 Release 页面文案、上传时间线与 changelog 是否还能从外部仓库或发布页补回
7. 如需执行临时目录物理清理，按脚本分阶段进行
   - 已确认：`scripts/cleanup_tmp_artifacts.ps1` 默认只做 dry-run，且默认保留被 session 文档引用的目录
   - 待确认：是否需要连 `tmp_bl002_record_smoke` 这类取证目录一起迁移或删除
8. 如需真正完成 Git 基线恢复，执行一次最小纳管提交
   - 已确认：当前建议纳管范围已经写入 `docs/sessions/2026-04-02-git-baseline-bl008.md`
   - 待确认：是否现在就执行 `git add` / `git commit`

## 优先级 P2
9. 继续观察并清理孤儿目录 / 空目录噪音
   - 例如：`deploy/`、`tmp7qf85p61/`、`tmpbape0idz/`

## 继续开发前建议
- 先读 `docs/handover/executable_backlog.md`
- 再读最近 session：
  - `docs/sessions/2026-04-01-docker-bl001-validation.md`
  - `docs/sessions/2026-04-01-client-bl002-smoke.md`
  - `docs/sessions/2026-04-01-flyinnas-bl004-validation.md`
  - `docs/sessions/2026-04-01-platform-coverage-bl005.md`
  - `docs/sessions/2026-04-01-config-sanitization-bl006.md`
  - `docs/sessions/2026-04-01-release-recovery-bl003.md`
  - `docs/sessions/2026-04-02-temp-cleanup-bl007.md`
  - `docs/sessions/2026-04-02-git-baseline-bl008.md`
- 如果准备继续 Docker / NAS 线，优先复用 `DOCKER_FLYINNAS.md`、`DOCKER_FLYINNAS_CHECKLIST.md`、`DOCKER_FLYINNAS_REGRESSION.md`
- 开始新任务前，先把“已确认 / 推断 / 待确认”三栏写清楚，避免把历史猜测当事实
