# 2026-04-02 BL-002 EXE Automation Probe

## 这次做了什么
- 先复核了打包版客户端的跨进程自动化现状。
- 确认外部 UIAutomation / `pywinauto` 只能稳定识别窗口与控件，不能稳定触发 Qt 打包版按钮动作。
- 将主方案切换为“进程内文件桥”：
  - 环境变量：`DLR_AUTOMATION_DIR`
  - 请求文件：`request.json`
  - 响应文件：`response.json`
- 在客户端中接入自动化命令分发，并新增 EXE 验收脚本。
- 重打包最新 EXE，重新验证 `start_task_debug` 与正式 `start_task`。
- 最终跑通完整打包版自动化验收。

## 关键文件
- `client/infra/process/automation_bridge.py`
- `client/bootstrap.py`
- `client/ui/main_window.py`
- `src/logger.py`
- `scripts/exe_automation_acceptance.py`
- `client/tests/test_automation_bridge.py`
- `client/tests/test_legacy_logger_windowed.py`

## 已确认事实
- 早先的 `Cannot log to objects of type 'NoneType'` 在旧 EXE/旧进程场景下出现；重打包并命中新包后未再复现。
- `start_task_debug` 在打包版 EXE 中已能真实起录。
- 正式 `start_task` 在打包版 EXE 中也已能真实起录。
- `scripts/exe_automation_acceptance.py` 已真实通过，链路如下：
  - `ping`
  - `add_task`
  - `start_task`
  - `stop_task`
  - `list_history`
  - `shutdown`
- 验收摘要：`tmp_bl002_exe_automation_run2/acceptance_summary.json`
- 真实录制产物：`tmp_bl002_exe_automation_run2/downloads/BL002_EXE_Automation/`

## 结论
- “打包版 Qt 跨进程自动化”当前已经打通。
- 当前推荐路线是文件桥，而不是继续投入外部 UIA 点按钮。
- 外部 UIA 探测结论仍有保留价值，但只适合作为旁证，不再作为主验收链路。

## 这次顺手补强
- `scripts/exe_automation_acceptance.py` 现会额外校验真实录制产物，并把 `output_files` 写入摘要，避免只有状态变化却没有文件时误判成功。

## 下一步建议
1. 把 handover 中关于“打包版自动化未打通”的旧结论全部收口为已完成。
2. 决定是否还保留“真人手点 EXE”作为可选项。
3. 若还要继续扩展自动化，优先扩展文件桥命令，不回退到外部点控路线。
