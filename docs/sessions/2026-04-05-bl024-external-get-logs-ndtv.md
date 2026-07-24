# 2026-04-05 BL-024 第二条外部源 get_logs 对照样本

## 本次做了什么
- 选用第二条外部公开新闻源 NDTV 作为 `BL-024` 样本。
- 先试了 `master.m3u8`，确认 `get_logs` 可用，但实际录制吞吐偏低。
- 最终改用 720p 子 playlist：
  - `https://ndtv24x7elemarchana.akamaized.net/hls/live/2003678/ndtv24x7/masterp_720p@3.m3u8`

## 验收命令

```powershell
& '.\.client-conda-env\python.exe' scripts\exe_get_logs_stability.py --repo-root . --workspace .\tmp_bl024_external_get_logs_run3 --stream-url https://ndtv24x7elemarchana.akamaized.net/hls/live/2003678/ndtv24x7/masterp_720p@3.m3u8 --display-name BL024_External_GetLogs_NDTV720 --record-seconds 300 --query-interval 1 --query-timeout 12 --log-limit 200 --split-seconds 86400
```

## 关键产物
- `tmp_bl024_external_get_logs_run3/acceptance_summary.json`

## 结果
- `success = true`
- `total_calls = 241`
- `successful_calls = 241`
- `failed_calls = 0`
- `max_latency_ms = 404.53`
- `avg_latency_ms = 248.87`

## 结论
- 第二条外部源 `get_logs` 对照样本已补齐。
- 当前外部源 `get_logs` 稳定性证据已不只覆盖 Global News，也覆盖 NDTV。
