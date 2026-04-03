# 当前可执行 Backlog

最后更新：2026-04-02

## 已完成（最近）

### BL-002 打包版 Qt 跨进程自动化
- 状态：已完成
- 已确认：
  - 文件桥 `client/infra/process/automation_bridge.py` 已接入打包版客户端
  - `client/ui/main_window.py` 已支持自动化命令分发
  - `scripts/exe_automation_acceptance.py` 已跑通完整 EXE 验收
  - 验收产物位于 `tmp_bl002_exe_automation_run2/`
- 备注：
  - 外部 UIAutomation 探测仍可保留为旁证
  - 但当前主方案已明确转为文件桥

### BL-004 Docker / NAS 真机验收
- 状态：已完成
- 已确认：
  - 本地 Docker 构建通过
  - NAS 真实 `first-deploy` / `upgrade-deploy` / `rollback-deploy` 通过

### BL-009 单文件约 1GB 自动切段
- 状态：已完成
- 已确认：
  - 录制过程中会按大小切段
  - 仍按博主目录落盘

### BL-011 评估是否保留真人手点 EXE
- 状态：已完成
- 已确认：
  - 当前文件桥自动化已覆盖核心录制验收链路：新增任务、启动录制、停止录制、历史落档、产物生成、关闭客户端
  - `tmp_bl002_exe_automation_run3/acceptance_summary.json` 已给出最新通过证据
  - 外部 UIAutomation 仅保留旁证价值，不再作为主验收路线
- 结论：
  - 真人手点打包版 EXE 降级为可选观察项
  - 不再作为发布前必做 backlog

### BL-012 扩展文件桥命令面
- 状态：已完成（第一轮）
- 已确认：
  - 已新增任务维护命令：`edit_task`、`delete_task`、`import_tasks`、`export_tasks`
  - 已新增日志命令：`get_logs`、`clear_logs`
  - 已新增页面命令：`list_tabs`、`set_current_tab`
  - `client/tests/test_automation_bridge.py` 已覆盖新增命令
- 结论：
  - 当前文件桥已从“最小录制验收”扩展到“可维护任务 + 可读日志 + 可切页”的更完整自动化面
  - 若后续继续扩展，建议作为第二轮增强单独立项

## 当前待执行

### BL-010 清理 ACL 异常目录
- 优先级：P0
- 目标：
  - 在管理员终端删除 `tmp7qf85p61/`
  - 在管理员终端删除 `tmpbape0idz/`
- 当前入口：
  - `scripts/remove_acl_orphans_admin.ps1`
  - `docs/sessions/2026-04-02-bl010-acl-orphan-cleanup.md`
