# 2026-04-03 BL-013 长时录制边界观察

## 这次做了什么
- 扩展 `scripts/exe_automation_acceptance.py`，让打包版 EXE 验收脚本支持：
  - `--max-file-size-gb`
  - `--loop-seconds`
  - `--poll-interval`
  - 录制期间主动轮询 `list_tasks` / `list_history`
  - 输出阈值、产物大小、超限偏差、是否发生切段
- 使用真实打包版客户端做了一轮“小阈值加速观察”，用于模拟“长时录制达到 1GB 后是否自动切段”。

## 实际执行
```powershell
.\.client-conda-env\python.exe scripts/exe_automation_acceptance.py `
  --workspace tmp_bl013_rollover_observation_run2 `
  --display-name BL013_Rollover_Observation `
  --record-seconds 20 `
  --max-file-size-gb 0.0002 `
  --poll-interval 1.0 `
  --command-timeout 25
```

## 关键产物
- 摘要：`tmp_bl013_rollover_observation_run2/acceptance_summary.json`
- 录制文件：
  - `tmp_bl013_rollover_observation_run2/downloads/BL013_Rollover_Observation/BL013_Rollover_Observation_2026-04-03_08-53-51_000.ts`

## 已确认事实
- 打包版 EXE 真实录制链路可跑通。
- 观察参数：
  - `record_seconds=20`
  - `max_file_size_gb=0.0002`
  - 阈值折算为 `214748` bytes
- 录制结束后只生成了 1 个文件，大小 `805768` bytes。
- 录制期间多次主动调用 `list_tasks`，输出路径始终未变化。
- 历史记录条数在录制期间和停止后都只有 1 条。
- 最终摘要中的 `rollover_detected=false`。

## 关键推断
- 当前“按文件大小自动切段”在真实打包版路径下没有真正生效。
- 高置信推断根因：
  - `client/core/ffmpeg_service.py` 在 `split_recording=true` 时返回模板路径 `..._%03d.ts`
  - `is_session_over_size_limit()` 直接对这个模板路径做 `exists()` / `stat()`
  - 模板路径不是实际输出文件，因此大小检测很可能永远不会命中

## 顺手发现
- `history.json` 中保存的 `file_path` 也是模板路径 `..._%03d.ts`，不是实际产物路径。
- `get_logs` 在本轮 EXE 观察中超时；脚本已降级处理，不再影响整轮验收成功与否。
- 当前环境里不能直接用 `python`，需要用 `.client-conda-env/python.exe`。

## 结论
- 本轮不是“切段通过”，而是“边界观察确认当前实现存在缺口”。
- `BL-009` 不应再按“完全完成”理解，后续应转入修复项处理。

## 下一步建议
1. 修复分段模式下的大小检测，改为跟踪当前实际输出分段文件。
2. 修复历史记录中的 `file_path`，避免继续写模板路径。
3. 补单测覆盖 `split_recording=true` 与 `%03d` 模板路径。
4. 修复后复跑同一条 EXE 观察命令，再决定是否追加更长时间的真实观察。
