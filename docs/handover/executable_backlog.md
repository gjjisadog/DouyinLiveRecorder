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

## 当前待执行

### BL-010 清理 ACL 异常目录
- 优先级：P0
- 目标：
  - 在管理员终端删除 `tmp7qf85p61/`
  - 在管理员终端删除 `tmpbape0idz/`
- 当前入口：
  - `scripts/remove_acl_orphans_admin.ps1`
  - `docs/sessions/2026-04-02-bl010-acl-orphan-cleanup.md`

### BL-011 评估是否保留真人手点 EXE
- 优先级：P1
- 说明：
  - 当前自动化桥已经覆盖“新增任务 / 启停录制 / 历史落档 / 产物生成”
  - 需要产品或验收口径上确认，是否还要额外做人工点击录像留档

### BL-012 如需增强自动化，扩展文件桥命令面
- 优先级：P2
- 可选方向：
  - 编辑任务
  - 删除任务
  - 导入导出
  - 日志页辅助查询
