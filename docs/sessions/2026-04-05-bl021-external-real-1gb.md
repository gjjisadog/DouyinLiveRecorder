# 2026-04-05 BL-021 外部长时真实 1GB 全量样本

## 本次做了什么
- 为补齐更强的发布前背书，实际执行了一轮“公开外部长时源 + 打包版 EXE + 真实 `1 GB` 阈值”的高成本长样本验收。
- 先对多个公开新闻 HLS 源做短时探测，最终选用更稳定、实拉速率更适合长样本的 Global News 源：
  - `https://live.corusdigitaldev.com/groupb/live/3062d0e3-ed4c-4f47-8482-95648250f4b8/live.isml/live-audio_1=96000-video=2499968.m3u8`

## 验收命令

```powershell
& '.\.client-conda-env\python.exe' scripts\exe_automation_acceptance.py --repo-root . --workspace .\tmp_bl021_external_real_1gb_run1 --stream-url https://live.corusdigitaldev.com/groupb/live/3062d0e3-ed4c-4f47-8482-95648250f4b8/live.isml/live-audio_1=96000-video=2499968.m3u8 --display-name BL021_External_GlobalNews_1GB --record-seconds 4500 --max-file-size-gb 1.0 --split-seconds 86400 --poll-interval 10 --log-limit 200
```

## 关键时间点
- 启动时间：`2026-04-04 23:22:34`
- 首次按大小切段时间：`2026-04-05 00:18:00`
- 停止时间：`2026-04-05 00:37:35`

## 关键产物
- `tmp_bl021_external_real_1gb_run1/acceptance_summary.json`

## 结果
- `success = true`
- `rollover_detected = true`
- 共 2 段文件：
  - `1072987252`
  - `392916052`
- 阈值：`1073741824` bytes
- `max_overshoot_bytes = 0`
- 第一段历史状态：`completed`
- 第二段历史状态：测试结束后的 `stopped`
- 录制日志在 `2026-04-05 00:18:00` 明确出现：
  - “录制文件已达到单文件上限，准备自动切换新文件”

## 当前结论
- 外部长时公开新闻源下，真实 `1 GB` 自动切段已被打包版客户端真实触发。
- 这轮样本没有出现此前公网 Mux 源那种“未达阈值先自然结束再重拉”的问题。
- 当前仓库已经同时具备：
  - 本地连续流真实 `1 GB` 验收样本
  - 外部长时公开新闻流真实 `1 GB` 验收样本

## 仍保留的边界
- 这轮外部真实 `1 GB` 证据来自单一公开新闻源，不等价于“所有外部源都已覆盖”。
- 如果还要继续补强，可再补一条不同平台或不同 CDN 的外部长时真实 `1 GB` 样本，或补一轮外部源 `get_logs` 对照样本。
