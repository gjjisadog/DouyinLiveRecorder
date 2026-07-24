# 2026-04-03 BL-019 测试源替换记录

## 本次做了什么
- 确认 `BL-019` 原公网 Mux 流样本不再适合作为最终验收依据。
- 更新 `scripts/exe_automation_acceptance.py`，补充 `--split-seconds`，避免再次被默认时间切段干扰。
- 新增 `scripts/local_hls_test_source.py`，在本机持续生成并暴露 HLS 测试流。
- 用本地 HLS 源完成一轮打包版冒烟，验证 `direct` 直链录制链路真实可用。
- 启动新的 `BL-019` 正式样本：`tmp_bl019_local_source_1gb_run1/`。

## 关键证据
- 公网流样本 `tmp_bl019_real_1gb_run2/client_data/history.json` 显示：
  - 前两段状态为 `completed`
  - 文件大小约 `766240060` bytes、`814726576` bytes
  - 说明并不是按 `1 GB` 阈值触发切段
- 本地流源信息：`tmp_local_hls_source/source_info.json`
  - 流地址：`http://127.0.0.1:18080/stream.m3u8`
  - 默认视频码率：`24 Mbps`
- 本地流冒烟样本：`tmp_bl019_local_source_smoke/acceptance_summary.json`
  - `success = true`
  - `split_seconds = 86400`
  - 单段输出文件大小：`111712796` bytes
  - `rollover_detected = false`

## 当前正式样本
- 工作区：`tmp_bl019_local_source_1gb_run1/`
- 启动时间：`2026-04-03 17:50:44`
- 命令：

```powershell
.\.client-conda-env\python.exe scripts\exe_automation_acceptance.py --repo-root . --workspace .\tmp_bl019_local_source_1gb_run1 --stream-url http://127.0.0.1:18080/stream.m3u8 --record-seconds 900 --max-file-size-gb 1.0 --split-seconds 86400 --poll-interval 5
```

- 当前已确认：
  - `client_data/history.json` 已出现 `running` 记录
  - 下载目录已生成实际输出文件
  - 本轮样本已经替代公网流 `run2`，作为 BL-019 的主观察对象

## 最终结果
- 结果文件：`tmp_bl019_local_source_1gb_run1/acceptance_summary.json`
- 结果摘要：
  - `success = true`
  - `rollover_detected = true`
  - 阈值：`1073741824` bytes
  - 共 3 段文件：
    - `1073444092`
    - `1075609664`
    - `645593504`
  - `max_overshoot_bytes = 1867840`
  - 最大超限占比约 `0.17%`
- 日志关键证据：
  - `17:56:30` 出现第一次“录制文件已达到单文件上限，准备自动切换新文件”
  - `18:02:16` 出现第二次同类日志
  - 说明至少前两段均由大小阈值触发自动切段，而不是流源自然结束
- 结论：
  - “替换 BL-019 测试源”已完成
  - 本地连续流样本已能稳定支撑真实 `1 GB` 量级切段观察
  - 当前 `1 MB` 安全余量仍有小幅超限，但已明显优于此前公网样本无法判定的状态

## 下一次继续时先做什么
1. 如果要继续调优，先基于 `tmp_bl019_local_source_1gb_run1/acceptance_summary.json` 评估 `1 MB` 安全余量是否要调整。
2. 如果要补对照证据，再找不会自然结束的外部长时直播源复跑一轮。
3. 继续推进时，优先转入 `BL-017 get_logs` 稳定性补样本。

## 继续提示词
- BL-019 换源已完成，请基于 `tmp_bl019_local_source_1gb_run1/acceptance_summary.json` 评估是否继续优化 1MB 安全余量，否则转入 BL-017。
