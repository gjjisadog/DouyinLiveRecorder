# 2026-04-03 BL-016 按大小切段阈值精度修正

## 本次做了什么
- 复盘 `BL-015` 的长时间观察结果，继续执行 `BL-016`。
- 先尝试仅降低运行态同步间隔：
  - `client/ui/pages/tasks_page.py`
  - 任务页状态同步从 `1500ms` 收紧到 `500ms`
  - 定时器改为 `Qt.PreciseTimer`
- 新增回归测试，锁定任务页运行态同步定时器配置：
  - `client/tests/test_task_import_export.py`
- 对打包版 EXE 做第一次复验：
  - 产物：`tmp_bl016_precision_tuning/acceptance_summary.json`
  - 结果：`max_overshoot_bytes` 从 `827691` bytes 只降到 `804755` bytes
- 为确认根因，做了一轮不改仓库的现场探测：
  - 观察到活跃段文件在录制中按 `262144` bytes 台阶增长
  - 关闭段文件时会集中补刷，最终文件显著大于运行中可见大小
- 在 `client/core/ffmpeg_service.py` 增加按阈值提前切段的安全余量策略。
- 新增核心回归测试：
  - `client/tests/test_core_services.py`
- 重新构建打包版并复验：
  - 产物：`tmp_bl016_guard_band_validation/acceptance_summary.json`
  - 结果：`0.001 GB` / 75 秒样本下 `max_overshoot_bytes = 0`

## 关键证据
- `tmp_bl015_long_run_observation/acceptance_summary.json`
  - 旧基线：3 段，最大超限 `827691` bytes
- `tmp_bl016_precision_tuning/acceptance_summary.json`
  - 仅提速轮询后，最大超限 `804755` bytes
- 现场探测输出
  - 运行中观测到段文件大小以 `262144` bytes 台阶增长
  - 当第一段切出时，运行中最后看到的是 `1048576` bytes，最终落盘变成 `1831684` bytes
- `tmp_bl016_guard_band_validation/acceptance_summary.json`
  - 安全余量策略后，75 秒样本切出 12 段，最大超限 `0`

## 结论
- `BL-016` 的主因不是单纯轮询太慢。
- 更关键的问题是：ffmpeg 段文件在运行时的磁盘大小滞后于最终落盘大小。
- 当前启发式安全余量策略能把小阈值压力样本压到“不超限”。
- 代价是：小阈值样本会明显更早切段，段数增多。

## 已修改文件
- `client/ui/pages/tasks_page.py`
- `client/core/ffmpeg_service.py`
- `client/tests/test_core_services.py`
- `client/tests/test_task_import_export.py`
- `docs/handover/current_status.md`
- `docs/handover/next_steps.md`
- `docs/handover/known_issues.md`
- `docs/handover/executable_backlog.md`

## 已执行验证
- `.\\.client-conda-env\\python.exe -m unittest client.tests.test_core_services`
- `.\\.client-conda-env\\python.exe -m unittest client.tests.test_task_import_export`
- `.\\.client-conda-env\\python.exe -m unittest client.tests.test_main_window_runtime`
- `.\\.client-conda-env\\python.exe -m unittest client.tests.test_automation_bridge`
- `.\\.client-conda-env\\python.exe -m client.build_release --python '.\\.client-conda-env\\python.exe' --repo-root .`
- `.\\.client-conda-env\\python.exe scripts\\exe_automation_acceptance.py --repo-root . --workspace .\\tmp_bl016_precision_tuning --record-seconds 75 --max-file-size-gb 0.001 --poll-interval 0.5`
- `.\\.client-conda-env\\python.exe scripts\\exe_automation_acceptance.py --repo-root . --workspace .\\tmp_bl016_guard_band_validation --record-seconds 75 --max-file-size-gb 0.001 --poll-interval 0.5`

## 下一步建议
- 优先做一轮更接近真实目标的长时间样本，验证 `BL-016` 安全余量在 `1 GB` 附近是否仍然合理。
- 若真实阈值样本切段偏早，再基于真实样本微调安全余量，而不是继续单独下调 UI 轮询间隔。
