# 2026-04-03 BL-019 真实 1GB 长时观察启动记录

## 本次做了什么
- 进入 `BL-019`，准备直接做真实 `1 GB` 长时观察。
- 先基于 `BL-018` 样本估算触发 `1 GB` 切段的大致时长。
- 结论：
  - 按 `BL-018` 的测得速率，触发 `1 GB` 切段约需 `3.76h`
  - 为确保覆盖至少一个完整切段，正式长测按 `record_seconds=18000` 启动

## 长测启动参数
- 首轮工作区：`tmp_bl019_real_1gb_run1/`
- 首轮标准输出日志：`tmp_bl019_runner_logs/stdout.log`
- 首轮标准错误日志：`tmp_bl019_runner_logs/stderr.log`
- 启动时间：`2026-04-03 11:29:56`
- 进程：
  - Python PID：`55240`
- 命令：

```powershell
.\.client-conda-env\python.exe scripts\exe_automation_acceptance.py --repo-root . --workspace .\tmp_bl019_real_1gb_run1 --record-seconds 18000 --max-file-size-gb 1.0 --poll-interval 30
```

## 启动过程中的实际情况
- 第一次启动失败。
  - 原因：我把重定向日志放进了工作区本身，`prepare_workspace()` 清理目录时被 `stderr.log` 占用卡住。
  - 处理：改成“日志写到工作区外”后重新启动。
- 第二次启动已确认成功。
- 后续确认首轮样本仍然无效。
  - 原因：`scripts/exe_automation_acceptance.py` 默认把 `split_seconds` 固定为 `1800`
  - 结果：在触发 `1GB` 大小切段之前，先被 30 分钟时间切段打断
  - 证据：
    - `tmp_bl019_real_1gb_run1/downloads/BL002_EXE_Automation_2026-04-03_11-31-29_000.ts`
    - 首段大小仅 `780375216` bytes，却已在 `12:51:30` 切到下一段

## 修正动作
- 已更新 `scripts/exe_automation_acceptance.py`
  - 新增参数：`--split-seconds`
- 已停止无效的 `run1`
- 已重启有效长测 `run2`

## run2 启动参数
- 工作区：`tmp_bl019_real_1gb_run2/`
- 标准输出日志：`tmp_bl019_runner_logs/stdout_run2.log`
- 标准错误日志：`tmp_bl019_runner_logs/stderr_run2.log`
- 启动时间：`2026-04-03 13:33:37`
- 进程：
  - 当前 Python PID：`46840`
- 命令：

```powershell
.\.client-conda-env\python.exe scripts\exe_automation_acceptance.py --repo-root . --workspace .\tmp_bl019_real_1gb_run2 --record-seconds 18000 --max-file-size-gb 1.0 --split-seconds 86400 --poll-interval 30
```

## 当前已确认状态
- 长测进程已存活并进入录制态。
- 工作区中已生成：
  - `client_data/tasks.json`
  - `client_data/history.json`
  - `downloads/`
- 当前已出现首个输出文件：
  - `downloads/BL002_EXE_Automation/BL002_EXE_Automation_2026-04-03_13-34-06_000.ts`
- 当前 `history.json` 为运行中记录，符合历史服务写法，不表示已经完成切段。

## run2 最新检查点
- 检查时间：`2026-04-03` 本线程继续时
- 结果：
  - 有效长测进程 `46840` 仍在运行
  - `tmp_bl019_real_1gb_run2/acceptance_summary.json` 尚未生成
  - 当前活跃段文件：
    - `BL002_EXE_Automation_2026-04-03_13-34-06_000.ts`
    - 当前大小：`323223552` bytes
  - 当前仍未发生第一次按大小切段

## run2 再次检查点
- 检查时间：`2026-04-03` 本线程再次继续时
- 结果：
  - 有效长测进程 `46840` 仍在运行
  - `tmp_bl019_real_1gb_run2/acceptance_summary.json` 仍未生成
  - 当前活跃段文件：
    - `BL002_EXE_Automation_2026-04-03_13-34-06_000.ts`
    - 当前大小：`660602880` bytes
  - 当前仍未发生第一次按大小切段

## run2 关键新发现
- 检查时间：`2026-04-03` 本线程再次继续时
- 结果：
  - `acceptance_summary.json` 仍未生成，但 `downloads/` 已经出现 3 段文件：
    - `BL002_EXE_Automation_2026-04-03_13-34-06_000.ts`：`766240060` bytes
    - `BL002_EXE_Automation_2026-04-03_15-44-11_000.ts`：`814726576` bytes
    - `BL002_EXE_Automation_2026-04-03_17-14-13_000.ts`：`231211008` bytes
  - `history.json` 显示：
    - 前两段状态是 `completed`
    - 第三段仍是 `running`
- 结论：
  - 这不是“等 1GB 再按大小切段”的单一路径
  - 当前测试流源或 ffmpeg 录制过程会在未达到 `1 GB` 时自然结束，然后由客户端再次拉起下一段
  - 因此 `run2` 目前不足以单独证明“真实 1GB 大小切段已经通过”

## 中途检查点
- 检查时间：`2026-04-03` 本线程继续时
- 结果：
  - 长测进程 `55240` 仍在运行
  - `acceptance_summary.json` 尚未生成
  - 当前仅有 1 个活跃段文件：
    - `BL002_EXE_Automation_2026-04-03_11-31-29_000.ts`
    - 当前大小：`113508352` bytes
  - 相对 `1 GB` 阈值进度：
    - 约 `10.57%`
    - 剩余约 `960233472` bytes
  - `history.json` 仍只有 1 条运行中记录，说明尚未发生第一次按大小切段

## 最新检查点
- 检查时间：`2026-04-03` 本线程再次继续时
- 结果：
  - 长测进程 `55240` 仍在运行
  - `acceptance_summary.json` 仍未生成
  - 当前活跃段文件：
    - `BL002_EXE_Automation_2026-04-03_11-31-29_000.ts`
    - 当前大小：`672661504` bytes
  - 相对 `1 GB` 阈值进度约 `62.65%`
  - 仍未发生第一次按大小切段

## 结果文件
- 长测真正完成后，应检查：
  - `tmp_bl019_real_1gb_run2/acceptance_summary.json`

## 下一次继续时先做什么
1. 检查长测进程是否仍在：
   - `Get-CimInstance Win32_Process -Filter "ProcessId = 46840"`
2. 若已完成，读取：
   - `tmp_bl019_real_1gb_run2/acceptance_summary.json`
3. 提取并记录：
   - `threshold_bytes`
   - `max_overshoot_bytes`
   - `max_overshoot_ratio`
   - 段数与各段大小
4. 更新：
   - `docs/handover/current_status.md`
   - `docs/handover/next_steps.md`
   - `docs/handover/known_issues.md`
   - `docs/handover/executable_backlog.md`

## 继续提示词
- “继续 BL-019，检查 `tmp_bl019_real_1gb_run2/acceptance_summary.json` 是否已生成；如果已完成，提取超限比例、段数、各段大小并更新 handover。”
