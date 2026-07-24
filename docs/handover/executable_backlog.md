# 当前可执行 Backlog

最后更新：2026-04-05

## 已完成

### BL-002 打包版 Qt 跨进程自动化
- 状态：已完成
- 已确认：
  - 文件桥 `client/infra/process/automation_bridge.py` 已接入打包版客户端
  - `scripts/exe_automation_acceptance.py` 可跑通真实 EXE 验收
  - 核心链路已验证：新增任务、启动录制、停止录制、历史落档、关闭客户端

### BL-004 Docker / NAS 真机验收
- 状态：已完成
- 已确认：
  - 本地 Docker 构建通过
  - NAS 侧 `first-deploy` / `upgrade-deploy` / `rollback-deploy` 有真实验收记录

### BL-009 单文件约 1GB 自动切段
- 状态：已完成
- 已确认：
  - 配置项、设置页、录制内核入口已经接入
  - `BL-013` 暴露了分段模式下模板路径导致的真实缺口
  - `BL-014` 已完成修复并通过打包版加速观察复验

### BL-010 清理 ACL 异常目录
- 状态：已完成
- 已确认：
  - `tmp7qf85p61/`、`tmpbape0idz/` 当前已不存在

### BL-011 评估是否保留真人手点 EXE
- 状态：已完成
- 结论：
  - 真人手点降级为可选观察项
  - 不再作为发布前必做门槛

### BL-012 扩展文件桥命令面
- 状态：已完成（第一轮）
- 已确认：
  - 已支持 `edit_task`、`delete_task`、`import_tasks`、`export_tasks`
  - 已支持 `list_tabs`、`set_current_tab`
  - 已支持 `get_logs`、`clear_logs`

### BL-013 长时录制 + 小阈值切段观察
- 状态：已完成
- 结论：
  - 观察完成并成功定位问题
  - 产物：`tmp_bl013_rollover_observation_run2/acceptance_summary.json`

### BL-014 修复分段模式下按大小切段失效
- 状态：已完成
- 已确认：
  - 修复 `%03d` 模板路径导致的大小检测失效
  - 修复历史记录落模板路径的问题
  - 回归测试通过：`client.tests.test_core_services`
  - 打包版复验通过：`tmp_bl014_rollover_fix_validation/acceptance_summary.json`
  - 20 秒小阈值观察内自动切出 3 段

### BL-015 长时间边界补观察
- 状态：已完成
- 已确认：
  - 产物：`tmp_bl015_long_run_observation/acceptance_summary.json`
  - 参数：`record_seconds=75`、`max_file_size_gb=0.001`
  - 75 秒内稳定完成 3 段录制
  - 历史记录与实际输出文件路径保持一致
- 观察结论：
  - 连续切段稳定性通过
  - 阈值精度仍偏粗，最大超限偏差达到 `827691` bytes

### BL-016 优化按大小切段的阈值精度
- 状态：已完成
- 已确认：
  - 代码修正：
    - `client/ui/pages/tasks_page.py`
    - `client/core/ffmpeg_service.py`
  - 已确认根因：
    - 仅降低 UI 轮询间隔，超限偏差只从 `827691` bytes 降到 `804755` bytes
    - 活跃段文件在录制中按 `262144` bytes 台阶落盘，关闭段文件时会集中补刷
  - 已落地改动：
    - 任务页运行态同步改为 `500ms` 精确定时器
    - 按大小切段判断补安全余量，避免等待磁盘大小精确达到阈值才切
  - 回归测试通过：
    - `client.tests.test_core_services`
    - `client.tests.test_task_import_export`
    - `client.tests.test_main_window_runtime`
    - `client.tests.test_automation_bridge`
  - 打包版复验：
    - `tmp_bl016_precision_tuning/acceptance_summary.json`
    - `tmp_bl016_guard_band_validation/acceptance_summary.json`
- 观察结论：
  - `0.001 GB` / 75 秒样本内 `max_overshoot_bytes = 0`
  - 小阈值压力样本切段更早，段数增加到 12 段

### BL-018 真实阈值长时观察
- 状态：已完成（第一轮缩比近真样本）
- 已确认：
  - 产物：`tmp_bl018_near_real_threshold/acceptance_summary.json`
  - 参数：`record_seconds=420`、`max_file_size_gb=0.01`
  - 说明：该样本用于逼近真实使用区间，不是真实 `1 GB` 全量观察
  - 420 秒内切出 4 段，历史记录与输出文件保持一致
  - 前 3 段大小：
    - `10897420`
    - `10897420`
    - `11041240`
  - 阈值：`10737418` bytes
  - 最大超限偏差：`303822` bytes
  - 最大超限占比：约 `2.83%`
- 观察结论：
  - 当前安全余量策略在更接近真实阈值的样本上仍有效
  - 切段频率已明显低于 `0.001 GB` 压力样本
  - 但仍需真实 `1 GB` 长样本做最终确认

### BL-020 外部长时源对照样本
- 状态：已完成
- 已确认：
  - 对照源：`https://abcnews-streams.akamaized.net/hls/live/2023566/abcnewshudson7/master_4000.m3u8`
  - 工作区：`tmp_bl020_external_control_abc_run1/`
  - 结果文件：`tmp_bl020_external_control_abc_run1/acceptance_summary.json`
  - 参数：`record_seconds=600`、`max_file_size_gb=0.01`、`split_seconds=86400`、`poll_interval=5`
  - 结果：
    - `success=true`
    - `rollover_detected=true`
    - 共 4 段文件
    - 前 3 段大小：
      - `9744604`
      - `9750808`
      - `9776000`
    - 最后一段为测试结束主动停止：`71816`
    - 阈值：`10737418` bytes
    - `max_overshoot_bytes = 0`
    - 录制日志中出现 3 次“录制文件已达到单文件上限，准备自动切换新文件”
- 结论：
  - 外部长时新闻流样本已补齐
  - 当前切段链路不只在本地连续流下有效，在更接近真实业务流的外部样本下同样稳定

### BL-021 外部长时真实 1GB 全量样本
- 状态：已完成
- 已确认：
  - 样本源：`https://live.corusdigitaldev.com/groupb/live/3062d0e3-ed4c-4f47-8482-95648250f4b8/live.isml/live-audio_1=96000-video=2499968.m3u8`
  - 工作区：`tmp_bl021_external_real_1gb_run1/`
  - 结果文件：`tmp_bl021_external_real_1gb_run1/acceptance_summary.json`
  - 参数：`record_seconds=4500`、`max_file_size_gb=1.0`、`split_seconds=86400`、`poll_interval=10`
  - 结果：
    - `success=true`
    - `rollover_detected=true`
    - 共 2 段文件
    - 第一段大小：`1072987252`
    - 第二段大小：`392916052`
    - 阈值：`1073741824` bytes
    - `max_overshoot_bytes = 0`
    - 第一段状态为 `completed`
    - 第二段状态为测试结束后的 `stopped`
    - 录制日志在 `2026-04-05 00:18:00` 明确出现“录制文件已达到单文件上限，准备自动切换新文件”
- 结论：
  - 外部长时公开新闻源下，真实 `1 GB` 自动切段已完成验收
  - 当前仓库已经同时具备本地真实 `1 GB` 与外部真实 `1 GB` 两档证据

### BL-022 外部源 `get_logs` 对照样本
- 状态：已完成
- 已确认：
  - 样本源：`https://live.corusdigitaldev.com/groupb/live/3062d0e3-ed4c-4f47-8482-95648250f4b8/live.isml/live-audio_1=96000-video=2499968.m3u8`
  - 工作区：`tmp_bl022_external_get_logs_run1/`
  - 结果文件：`tmp_bl022_external_get_logs_run1/acceptance_summary.json`
  - 参数：`record_seconds=300`、`query_interval=1`、`query_timeout=12`、`log_limit=200`
  - 结果：
    - `success=true`
    - `total_calls=240`
    - `successful_calls=240`
    - `failed_calls=0`
    - `max_latency_ms = 404.22`
    - `avg_latency_ms = 250.36`
- 结论：
  - 外部源录制过程中，`get_logs` 已完成对照验收
  - 当前仓库已经同时具备本地连续流与外部公开新闻流两档 `get_logs` 稳定性证据

## 验收详情（已完成）

### BL-019 真实 1GB 长时观察
- 优先级：P1
- 状态：已完成（本地连续流验收样本）
- 已执行：
  - `run1`：
    - 工作区：`tmp_bl019_real_1gb_run1/`
    - 已确认无效，原因是默认 `split_seconds=1800` 先触发了时间切段
  - `run2`：
    - 启动时间：`2026-04-03 13:33:37`
    - 工作区：`tmp_bl019_real_1gb_run2/`
    - 参数：`record_seconds=18000`、`max_file_size_gb=1.0`、`split_seconds=86400`、`poll_interval=30`
    - 已确认不适合作为最终验收依据
    - 当前新增观察：
      - 已生成 3 段文件
      - 前两段大小约 `766240060` bytes、`814726576` bytes
      - `history.json` 中前两段状态均为 `completed`
      - 说明当前公网流会在未达到 `1 GB` 前自然完成并被重新拉起
  - 测试源替换：
    - 已新增本地连续流脚本：`scripts/local_hls_test_source.py`
    - 本地流地址：`http://127.0.0.1:18080/stream.m3u8`
    - 冒烟样本：`tmp_bl019_local_source_smoke/acceptance_summary.json`
    - 冒烟结论：
      - `success=true`
      - 35 秒内单段录制 `111712796` bytes
      - 已证明本地流可被打包版 EXE 稳定录制
  - 当前正式样本：
    - 工作区：`tmp_bl019_local_source_1gb_run1/`
    - 启动时间：`2026-04-03 17:50:44`
    - 参数：`record_seconds=900`、`max_file_size_gb=1.0`、`split_seconds=86400`、`poll_interval=5`
    - 验收结果：
      - 结果文件：`tmp_bl019_local_source_1gb_run1/acceptance_summary.json`
      - `success=true`
      - `rollover_detected=true`
      - 共 3 段文件
      - 段大小：
        - `1073444092`
        - `1075609664`
        - `645593504`
      - 阈值：`1073741824` bytes
      - `max_overshoot_bytes = 1867840`
      - 最大超限占比约 `0.17%`
      - 日志已出现两次“录制文件已达到单文件上限，准备自动切换新文件”
- 结论：
  - 已确认本地连续流下，`1 GB` 按大小自动切段链路真实可用
  - 当前 `1 MB` 安全余量未完全消除超限，但超限已压到较低比例

### BL-017 观察打包版 `get_logs` 稳定性
- 优先级：P2
- 状态：已完成
- 已执行：
  - 新增专项脚本：`scripts/exe_get_logs_stability.py`
  - `run1`：
    - 工作区：`tmp_bl017_get_logs_stability_run1/`
    - 参数：`record_seconds=90`、`query_interval=2`
    - 结果：`40/40` 次 `get_logs` 成功
    - 延迟：`max_latency_ms = 403.82`、`avg_latency_ms = 252.19`
  - `run2`：
    - 工作区：`tmp_bl017_get_logs_stability_run2/`
    - 结果：样本无效
    - 原因：本地 HLS 源未成功绑定端口 `18080`
    - 处置：脚本已改为自动选择空闲端口，并在启动后实际探活 `.m3u8`
  - `run3`：
    - 工作区：`tmp_bl017_get_logs_stability_run3/`
    - 参数：`record_seconds=60`、`query_interval=1`
    - 结果：`49/49` 次 `get_logs` 成功
    - 延迟：`max_latency_ms = 402.4`、`avg_latency_ms = 246.4`
  - `run4`：
    - 工作区：`tmp_bl017_get_logs_stability_run4/`
    - 参数：`record_seconds=20`、`query_interval=1`
    - 结果：`16/16` 次 `get_logs` 成功
    - 延迟：`max_latency_ms = 406.09`、`avg_latency_ms = 252.78`
- 结论：
  - 在本地连续流打包版链路下，`get_logs` 已累计 `105/105` 成功
  - 当前未复现 BL-013 中的超时问题
  - 可视为“当前桥接方案下已稳定”

## 当前待执行

### BL-023 第二条外部长时真实 1GB 全量样本
- 优先级：P3
- 状态：已启动，待继续
- 目标：
  - 如果需要更强背书，再补一条不同平台或不同 CDN 的外部长时真实 `1 GB` 全量样本
- 已执行：
  - 已修复带 query 的直链 HLS 会被识别成 `unknown` 的问题，并重打包客户端
  - 已验证第二外部源候选 `23 ABC / Uplynk` 可在打包版 EXE 中按 `direct` 启动录制
  - 短样本：
    - `tmp_bl023_external_uplynk_probe2/acceptance_summary.json`
    - `120s` 产物大小：`29022500` bytes
  - 长样本尝试：
    - `tmp_bl023_external_real_1gb_run2/acceptance_summary.json`
    - 中断前已录到 `591921152` bytes
    - 中断原因为脚本读取 `response.json` 时遭遇 Windows 文件锁
  - 已补处理：
    - `scripts/exe_automation_acceptance.py` 现已对 `response.json` 的 `PermissionError` 做重试
- 当前边界：
  - 当前外部真实 `1 GB` 证据仍只有 `BL-021` 的 Global News 样本
  - `23 ABC / Uplynk` 当前时段的真实落盘速率低于预期，若继续用该源需要更长录制窗口
  - 该项仍是增强项，不是阻塞项

### BL-024 第二条外部源 `get_logs` 对照样本
- 优先级：P3
- 状态：已完成
- 已确认：
  - 样本源：`https://ndtv24x7elemarchana.akamaized.net/hls/live/2003678/ndtv24x7/masterp_720p@3.m3u8`
  - 工作区：`tmp_bl024_external_get_logs_run3/`
  - 结果文件：`tmp_bl024_external_get_logs_run3/acceptance_summary.json`
  - 参数：`record_seconds=300`、`query_interval=1`、`query_timeout=12`、`log_limit=200`
  - 结果：
    - `success=true`
    - `total_calls=241`
    - `successful_calls=241`
    - `failed_calls=0`
    - `max_latency_ms = 404.53`
    - `avg_latency_ms = 248.87`
- 结论：
  - 第二条外部源 `get_logs` 对照样本已补齐
  - 当前外部源 `get_logs` 证据已同时覆盖 Global News 与 NDTV 两条公开新闻流

### BL-025 文件桥继续扩展
- 优先级：P3
- 状态：可继续推进
- 目标：
  - 沿当前进程内文件桥继续补命令面或增强健壮性
  - 保持真实 EXE 自动化能力可复用
- 当前边界：
  - 不建议回退到外部 UIAutomation / `pywinauto` 点击方案
