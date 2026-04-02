# 2026-04-02 File Size Rollover

## 本次做了什么
- 在客户端录制内核中补了“单文件大小上限”配置，默认值为 `1.0 GB`。
- 保持现有“按主播分目录”逻辑不变，并明确沿用到新分段文件。
- 在 `RecordWorker.sync_task()` 中接入按文件大小自动切段：
  - 当当前输出文件达到上限时
  - 自动结束当前 `ffmpeg`
  - 自动启动下一段新文件
- 在设置页新增“单文件上限”输入项，支持本地配置落盘与回读。

## 已确认
- `client/core/ffmpeg_service.py` 已能判断当前录制文件是否达到大小上限。
- `client/core/record_worker.py` 已在运行中检测到超限时自动切到下一段。
- `client/core/models.py` / `client/core/config_service.py` 已新增并持久化 `max_file_size_gb`。
- `client/ui/pages/settings_page.py` 已新增“单文件上限”设置项。
- 现有按主播目录逻辑仍在：
  - 输出路径继续优先落到 `downloads/<主播名>/...`
- 相关回归已通过：
  - `client.tests.test_core_services`
  - `client.tests.test_settings_page`
- 额外编译检查已通过：
  - `python -m py_compile client/core/models.py client/core/config_service.py client/core/ffmpeg_service.py client/core/record_worker.py client/ui/pages/settings_page.py client/tests/test_core_services.py client/tests/test_settings_page.py`

## 推断
- 在当前客户端架构下，这种“运行中轮询文件大小并切段”的方案已经足够满足“单文件不超过 1G 且持续录制”的目标。
- 由于按主播分目录原本就已存在，本次需求的核心新增点其实是“按大小自动切段”。

## 待确认
- 真实长时间录制时，切段边界是否会因为轮询间隔而出现少量超出 `1 GB` 的情况。
- 打包版 `EXE` 下，这一行为是否仍与源码入口完全一致；当前本轮主要验证的是内核与设置回归。

## 结论
- 当前客户端已支持：
  - 自动按主播写入对应目录
  - 默认将单个录制文件控制在约 `1 GB` 上下，并自动切到下一段
