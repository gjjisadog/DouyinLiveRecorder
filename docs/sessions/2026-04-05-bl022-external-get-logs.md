# 2026-04-05 BL-022 外部源 get_logs 对照样本

## 本次做了什么
- 为补齐外部源下的 `get_logs` 稳定性证据，对现有 `scripts/exe_get_logs_stability.py` 做了最小补强：
  - 新增 `--stream-url`
  - 新增 `--display-name`
  - 当指定外部 `stream_url` 时，跳过本地 HLS 源启动流程
- 然后使用 Global News 外部公开 HLS 源跑了一轮 5 分钟外部源 `get_logs` 对照样本。

## 验收命令

```powershell
& '.\.client-conda-env\python.exe' scripts\exe_get_logs_stability.py --repo-root . --workspace .\tmp_bl022_external_get_logs_run1 --stream-url https://live.corusdigitaldev.com/groupb/live/3062d0e3-ed4c-4f47-8482-95648250f4b8/live.isml/live-audio_1=96000-video=2499968.m3u8 --display-name BL022_External_GetLogs_GlobalNews --record-seconds 300 --query-interval 1 --query-timeout 12 --log-limit 200 --split-seconds 86400
```

## 关键产物
- `tmp_bl022_external_get_logs_run1/acceptance_summary.json`

## 结果
- `success = true`
- `total_calls = 240`
- `successful_calls = 240`
- `failed_calls = 0`
- `max_latency_ms = 404.22`
- `avg_latency_ms = 250.36`
- 样本录制链路正常启动、正常停止，未出现超时或失败

## 当前结论
- 外部公开新闻源录制过程中，`get_logs` 已通过稳定性对照验收。
- 当前仓库已经同时具备：
  - 本地连续流 `get_logs` 稳定性样本
  - 外部公开新闻流 `get_logs` 稳定性样本

## 仍保留的边界
- 当前外部源 `get_logs` 证据仍主要来自单一公开新闻源。
- 如果还要继续补强，可再补一条不同平台或不同 CDN 的外部源 `get_logs` 对照样本。
