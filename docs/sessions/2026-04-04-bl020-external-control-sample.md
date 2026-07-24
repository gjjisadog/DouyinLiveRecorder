# 2026-04-04 BL-020 外部长时源对照样本

## 本次做了什么
- 为“更贴近真实业务流”的补证，选择一条当前可访问的外部 HLS 新闻直播流做长样本对照。
- 先用 `ffprobe` 与 `ffmpeg` 15 到 20 秒短录验证候选源可访问、可真实拉流。
- 最终选用：
  - `https://abcnews-streams.akamaized.net/hls/live/2023566/abcnewshudson7/master_4000.m3u8`
- 使用现有打包版 EXE 验收脚本补跑 10 分钟样本。

## 验收命令

```powershell
.\.client-conda-env\python.exe scripts\exe_automation_acceptance.py --repo-root . --workspace .\tmp_bl020_external_control_abc_run1 --stream-url https://abcnews-streams.akamaized.net/hls/live/2023566/abcnewshudson7/master_4000.m3u8 --display-name BL020_External_ABC_Control --record-seconds 600 --max-file-size-gb 0.01 --split-seconds 86400 --poll-interval 5
```

## 关键产物
- `tmp_bl020_external_control_abc_run1/acceptance_summary.json`

## 已确认结果
- `success = true`
- `rollover_detected = true`
- 阈值：`10737418` bytes
- 共 4 段文件：
  - `9744604`
  - `9750808`
  - `9776000`
  - `71816`
- `max_overshoot_bytes = 0`
- 日志中出现 3 次“录制文件已达到单文件上限，准备自动切换新文件”

## 关键结论
- 这轮外部样本没有出现此前公网 Mux 样本那种“未达阈值先自然结束、再由客户端重拉”的现象。
- 当前切段链路不仅在本地连续流下有效，在更接近真实业务流的外部新闻直播流下也可稳定工作。
- 但这仍是 `0.01 GB` 缩比对照，不是外部 `1 GB` 全量样本。

## 下一次继续时建议
1. 如果只是为了发布前证据，当前本地 `1 GB` 样本 + 外部 `0.01 GB` 对照样本已经足够成体系。
2. 如果还要再往上补强，只剩“外部长时源真实 `1 GB` 全量样本”这一档高成本验证。
