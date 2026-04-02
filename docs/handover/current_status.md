# 当前状态

最后更新：2026-04-02

## 已确认
- 仓库同时包含两条主线：
  - 旧版 CLI / 脚本录制主线：`main.py`、`src/`
  - 新版 PySide6 客户端主线：`client/`
- 客户端主窗口、任务页、设置页、历史页、日志页、通知、调度、托盘、任务持久化都已落地。
- Docker / NAS 侧的本地构建、镜像导出上传、`first-deploy` / `upgrade-deploy` / `rollback-deploy` 已有真实验收记录。
- “单文件约 1GB 自动切段 + 按博主目录落盘” 已接入客户端录制链路。
- 打包版客户端 `dist/DouyinLiveRecorder Client/DouyinLiveRecorder Client.exe` 当前已能真实启动。
- 打包版 Qt 跨进程自动化已经从“外部 UIA 点按钮”切到“进程内文件桥”方案：
  - 启用条件：设置环境变量 `DLR_AUTOMATION_DIR`
  - 客户端轮询 `request.json`
  - 客户端回写 `response.json`
  - 已支持 `ping`、`add_task`、`start_task`、`stop_task`、`list_tasks`、`list_history`、`shutdown`
- 2026-04-02 已真实跑通打包版自动化验收：
  - 重打包后，`start_task_debug` 与正式 `start_task` 均成功起录
  - `scripts/exe_automation_acceptance.py` 已跑通完整链路：新增任务 → 启动录制 → 停止录制 → 历史落档 → 关闭客户端
  - 验收产物位于 `tmp_bl002_exe_automation_run2/`
  - `tmp_bl002_exe_automation_run2/acceptance_summary.json` 显示 `success: true`
  - `tmp_bl002_exe_automation_run2/downloads/BL002_EXE_Automation/` 下已生成真实录制文件
- 为避免“状态通过但没产物”的误判，`scripts/exe_automation_acceptance.py` 现已补充录制产物校验，并会把 `output_files` 写入验收摘要。

## 推断
- 之前出现的 `Cannot log to objects of type 'NoneType'` 不是当前代码根因，更可能是旧 EXE / 旧进程未被完全替换导致的历史误判。
- 打包版自动化的推荐长期方案应继续使用“进程内自动化桥”，而不是回到脆弱的外部 UIA 点击。

## 待确认
- 是否还需要保留“真人手点打包版 EXE”作为发布前必做门槛；从工程闭环角度看，当前自动化桥已能覆盖核心录制链路。
- 外部 UIAutomation / `pywinauto` 是否还值得继续投入；当前只确认“能识别控件”，不再是主推荐路线。
- `tmp7qf85p61/`、`tmpbape0idz/` 两个 ACL 异常目录仍需管理员终端清理。
- 管理员清理入口已补：`scripts/remove_acl_orphans_admin.ps1`

## 建议先看
- `README.md`
- `CLIENT_TASK_TRACKER.md`
- `client/infra/process/automation_bridge.py`
- `client/ui/main_window.py`
- `scripts/exe_automation_acceptance.py`
- `scripts/remove_acl_orphans_admin.ps1`
- `docs/sessions/2026-04-02-bl002-exe-automation-probe.md`
