# 2026-04-04 BL-017 打包版 get_logs 稳定性观察

## 本次做了什么
- 为 `BL-017` 新增专项验收脚本 `scripts/exe_get_logs_stability.py`。
- 该脚本会：
  - 自动启动本地 HLS 连续流源
  - 启动打包版 `DouyinLiveRecorder Client.exe`
  - 创建 `direct` 任务并开始录制
  - 在录制过程中循环调用 `get_logs`
  - 汇总成功率、延迟、失败明细和最终日志快照
- 中途顺手修正了脚本层两个问题：
  - 本地源工作区改为每轮独立
  - 本地源改为自动选择空闲端口，并在启动后实际探活 `.m3u8`

## 样本结果

### run1
- 工作区：`tmp_bl017_get_logs_stability_run1/`
- 命令：

```powershell
.\.client-conda-env\python.exe scripts\exe_get_logs_stability.py --repo-root . --workspace .\tmp_bl017_get_logs_stability_run1 --record-seconds 90 --query-interval 2 --query-timeout 12 --log-limit 120
```

- 结果：
  - `40/40` 次 `get_logs` 成功
  - `max_latency_ms = 403.82`
  - `avg_latency_ms = 252.19`

### run2
- 工作区：`tmp_bl017_get_logs_stability_run2/`
- 结果：无效样本
- 根因：
  - 本地 HLS 源未成功绑定 `18080`
  - 老版本脚本仅凭 `source_info.json` 存在就认为源端可用
- 处理：
  - 让脚本自动挑空闲端口
  - 改为启动后实际请求 `.m3u8` 做探活

### run3
- 工作区：`tmp_bl017_get_logs_stability_run3/`
- 命令：

```powershell
.\.client-conda-env\python.exe scripts\exe_get_logs_stability.py --repo-root . --workspace .\tmp_bl017_get_logs_stability_run3 --record-seconds 60 --query-interval 1 --query-timeout 12 --log-limit 200 --port 18081
```

- 结果：
  - `49/49` 次 `get_logs` 成功
  - `max_latency_ms = 402.4`
  - `avg_latency_ms = 246.4`

### run4
- 工作区：`tmp_bl017_get_logs_stability_run4/`
- 说明：这是脚本加固后的短样本复验
- 结果：
  - `16/16` 次 `get_logs` 成功
  - `max_latency_ms = 406.09`
  - `avg_latency_ms = 252.78`

## 关键结论
- `BL-013` 中出现过的 `get_logs` 超时，本轮未复现。
- 有效样本累计：
  - `105/105` 次 `get_logs` 成功
- 当前观察到的响应特征：
  - 常态大约 `200ms`
  - 部分轮次大约 `400ms`
  - 没有出现超时或失败响应
- 因此 `BL-017` 可以按“已完成”处理。

## 关键产物
- `tmp_bl017_get_logs_stability_run1/acceptance_summary.json`
- `tmp_bl017_get_logs_stability_run2/acceptance_summary.json`
- `tmp_bl017_get_logs_stability_run3/acceptance_summary.json`
- `tmp_bl017_get_logs_stability_run4/acceptance_summary.json`

## 下一次继续时建议
1. 如果还要补发布前证据，可以找一个不会自然结束的外部长时直播源，再跑一轮对照样本。
2. 如果不需要外部源对照，优先回到“1GB 安全余量是否继续微调”的决策。
