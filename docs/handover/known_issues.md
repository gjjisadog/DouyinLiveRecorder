# 已知问题

最后更新：2026-04-10

## Docker 配置页
- 当前配置页默认无鉴权，适合局域网或受控 NAS 环境；如果需要公网暴露，应自行通过反向代理、白名单或额外认证保护。
- 配置页只管理 `config/URL_config.ini`，不会覆盖 `config/config.ini` 中的 Cookie、推送和账号密码配置。
- 配置页的增删停用会直接改写挂载文件；如果宿主机同时手工编辑同一文件，最后一次写入会生效。
- 日志控制台当前只支持查看固定日志文件 `streamget.log` 与 `PlayURL.log`，还不支持搜索、下载或自动刷新。
- 飞牛面板“链接图标”目前没有查到明确公开的专用 Compose label 规范；当前采用的是更保守的兼容策略：
  - 稳定运行的容器
  - 固定端口映射
  - 常驻可访问的 Web 页面

## 已确认问题
- 当前 shell 的 `python` 指向 Windows Store 别名，不可直接用于项目脚本。
  - 已确认可用解释器：`.client-conda-env/python.exe`
- 当前按大小切段的精度问题已通过启发式安全余量明显缓解，但外部真实 `1 GB` 证据目前仍主要来自单一公开新闻源。
  - 旧证据：
    - `tmp_bl014_rollover_fix_validation/acceptance_summary.json`
    - `tmp_bl015_long_run_observation/acceptance_summary.json`
  - 新证据：
    - `tmp_bl016_precision_tuning/acceptance_summary.json`
    - `tmp_bl016_guard_band_validation/acceptance_summary.json`
    - `tmp_bl018_near_real_threshold/acceptance_summary.json`
  - 已确认根因：
    - 运行中段文件磁盘大小按 `262144` bytes 台阶增长
    - 切段/停止时会集中补刷，导致“运行中看到的大小”显著小于“最终落盘大小”
  - 当前残留问题：
    - 小阈值样本虽然已不超限，但会更早切段、段数增多
    - `0.01 GB` 缩比样本已回到较低超限占比，但仍不能直接等价为真实 `1 GB` 结论
- 公网 Mux 测试流不适合继续承担 `BL-019` 的最终验收样本。
  - 证据：`tmp_bl019_real_1gb_run2/client_data/history.json`
  - 现象：
    - 前两段均以 `completed` 结束
    - 文件大小分别约 `766240060` bytes、`814726576` bytes
    - 都明显小于 `1 GB`
  - 已处理：
    - `BL-019` 已切换到本地 HLS 连续流源
    - 本地源脚本：`scripts/local_hls_test_source.py`
    - 本地源冒烟样本：`tmp_bl019_local_source_smoke/acceptance_summary.json`
  - 已补充结果：
    - `tmp_bl019_local_source_1gb_run1/acceptance_summary.json` 已落盘
    - 已确认按大小自动切段真实发生
    - 当前本地连续流样本最大超限为 `1867840` bytes，约 `0.17%`

## 已缓解
- 分段录制开启时，按文件大小自动切段在真实打包版链路下此前失效的问题，已修复并通过复验。
- 历史记录此前保存模板路径 `..._%03d.ts` 的问题，已修复为保存实际分段文件路径。
- `BL-016` 已把 `0.001 GB` / 75 秒打包样本的 `max_overshoot_bytes` 压到 `0`。
- `BL-018` 已确认 `0.01 GB` / 420 秒缩比近真样本的最大超限为 `303822` bytes，占阈值约 `2.83%`。
- ACL 异常目录 `tmp7qf85p61/`、`tmpbape0idz/` 已清理，不再干扰仓库扫描。
- 打包版 EXE 自动化已改用进程内文件桥，不再依赖脆弱的外部 UIAutomation 点击链路。

## 待确认
- 除 Global News 这条外部公开新闻源外，其他外部长时源在真实 `1 GB` 阈值下是否同样稳定。
- 当前 `1 MB` 安全余量在 `1 GB` 阈值下仍存在小幅超限，但项目当前决定不再继续微调。
  - 证据：`tmp_bl019_local_source_1gb_run1/acceptance_summary.json`
  - 现象：
    - 第一段 `1073444092` bytes，未超限
    - 第二段 `1075609664` bytes，超限 `1867840` bytes
  - 当前决策：
    - 将该结果视为可接受范围
    - 不再继续调高安全余量或追加阈值策略优化

## 已澄清
- `BL-013` 中出现过的 `get_logs` 超时，本轮 `BL-017` 未复现。
  - 证据：
    - `tmp_bl017_get_logs_stability_run1/acceptance_summary.json`
    - `tmp_bl017_get_logs_stability_run3/acceptance_summary.json`
    - `tmp_bl017_get_logs_stability_run4/acceptance_summary.json`
  - 当前结论：
    - 本地连续流样本下累计 `105/105` 次 `get_logs` 调用成功
    - 常态响应约 `200ms`，部分轮次约 `400ms`
- `BL-017` 过程中出现过一次失败样本，但根因不是 `get_logs`。
  - 失败样本：`tmp_bl017_get_logs_stability_run2/acceptance_summary.json`
  - 原因：
    - 本地 HLS 源端口 `18080` 被占用，源进程未能成功绑定
    - 同时暴露出旧脚本对“source_info 已写出即代表源已可访问”的假设过强
  - 已处理：
    - `scripts/exe_get_logs_stability.py` 现已改为自动挑空闲端口
    - 并在启动后实际探活本地 `.m3u8`，避免带着假阳性源继续验收
- “需要补一轮更贴近真实业务流的外部长样本”这一项已完成。
  - 证据：`tmp_bl020_external_control_abc_run1/acceptance_summary.json`
  - 样本源：ABC News 外部 HLS 直播流
  - 当前结论：
    - 外部长样本已在 `0.01 GB` 阈值下稳定切段
    - 未观察到此前公网 Mux 样本那种“未达阈值先自然结束再重拉”的现象
- `BL-020` 当前补到的是外部长时 `0.01 GB` 对照样本，不等价于外部长时真实 `1 GB` 全量证明。
- 上述边界已由 `BL-021` 部分补齐。
  - 证据：`tmp_bl021_external_real_1gb_run1/acceptance_summary.json`
  - 当前结论：
    - 已在公开外部长时新闻源上真实跑到 `1 GB` 并触发自动切段
    - 第一段 `1072987252` bytes，`max_overshoot_bytes = 0`
    - 当前剩余边界不再是“是否存在外部真实 `1 GB` 证据”，而是“外部真实 `1 GB` 证据是否需要覆盖更多源”
- `get_logs` 外部源稳定性边界已由 `BL-022` 部分补齐。
  - 证据：`tmp_bl022_external_get_logs_run1/acceptance_summary.json`
  - 当前结论：
    - 已在公开外部新闻源录制过程中完成 `240/240` 次 `get_logs` 成功调用
    - `max_latency_ms = 404.22`
    - 当前剩余边界不再是“外部源下是否存在 `get_logs` 证据”，而是“是否需要覆盖更多外部源”
- `BL-024` 已进一步补到第二条外部源 `get_logs` 证据。
  - 证据：`tmp_bl024_external_get_logs_run3/acceptance_summary.json`
  - 当前结论：
    - 已在 NDTV 外部公开新闻源录制过程中完成 `241/241` 次 `get_logs` 成功调用
    - `max_latency_ms = 404.53`
    - 这一边界现已基本收口
- `BL-023` 当前真正的剩余风险不再是“有没有第二条外部源候选”，而是“候选源是否能在可接受时长内真实跑到 `1 GB`”。
  - 已确认可录制候选：`23 ABC / Uplynk`
  - 短样本：`tmp_bl023_external_uplynk_probe2/acceptance_summary.json`
  - 长样本尝试：`tmp_bl023_external_real_1gb_run2/acceptance_summary.json`
  - 当前现象：
    - 该源在当前时段真实落盘速率低于 playlist 标称码率
    - `5100s` 长样本在脚本读取 `response.json` 时被 Windows 文件锁打断，中断前单段文件仅到 `591921152` bytes
  - 已处理：
    - `scripts/exe_automation_acceptance.py` 已对 `response.json` 的空 JSON / 半写 JSON / `PermissionError` 补重试
  - 当前剩余边界：
    - 若继续用该源，需要更长录制窗口

## 抖音 Docker daemon

- ARMv7 已通过 buildx/QEMU 构建与运行时验证，但尚未在真实 ARMv7 设备上完成
  长时间录制，因此仍是允许失败的实验目标；正式发布仅含 AMD64 和 ARM64。
- NAS 旧配置本身仅有 1 个启用房间；当前通过 2 个公开热门直播测试地址补足
  多房间观察，但公开直播可能随时下播，因此 24 小时内的并发录制数不保证恒为 2。
- Cookie 缺失时部分直播间或原画可能不可用，daemon 会告警但不会把 Cookie
  内容写入日志。
- 抖音风控返回结构可能随站点升级变化；当前解析继续复用 `src/spider.py`，
  已开始收集脱敏分类样本，但尚未建立覆盖所有风控响应的离线样本库。
- 真实容器 `docker stop` 验收依赖本机 Docker daemon；本地自动化测试已覆盖
  FFmpeg SIGINT 后 TS 可被 `ffprobe` 解析。
