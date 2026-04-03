# 2026-04-03 BL-011 EXE Manual Gate Decision

## 这次做了什么
- 基于仓库内现有证据，对 `BL-011` 进行了正式评估。
- 目标是判断“真人手点打包版 EXE”是否还应保留为发布前必做门槛。

## 参考证据
- `docs/sessions/2026-04-02-bl002-exe-automation-probe.md`
- `tmp_bl002_exe_automation_run3/acceptance_summary.json`
- `scripts/exe_automation_acceptance.py`
- `client/infra/process/automation_bridge.py`
- `client/ui/main_window.py`

## 已确认
- 打包版 EXE 已真实跑通以下链路：
  - `ping`
  - `add_task`
  - `start_task`
  - `stop_task`
  - `list_history`
  - `shutdown`
- 真实录制产物已生成，并且验收脚本已校验 `output_files`。
- 外部 UIAutomation / `pywinauto` 当前只能作为“控件可见性旁证”，不能作为稳定主链路。

## 结论
- `BL-011` 判定完成。
- 真人手点打包版 EXE 从现在起降级为“可选观察项”。
- 只要文件桥自动化验收继续可用，就不再把真人手点作为发布前必做门槛。

## 适用边界
- 这个结论适用于当前仓库中的 MVP / 客户端发布验收口径。
- 如果未来出现以下情况，可以再临时恢复人工点击：
  - 文件桥命令接口发生大改且未同步验收脚本
  - 需要做演示录像或非技术人员体验确认
  - 发布策略要求额外留存人工观察证据

## 下一步建议
1. 继续执行 `BL-010` 的管理员目录清理。
2. 如还要继续做客户端自动化增强，直接推进 `BL-012`。
