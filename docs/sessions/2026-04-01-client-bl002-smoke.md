# 2026-04-01 Client BL-002 Smoke

## 本次做了什么
- 先验证 `ffmpeg` 依赖，发现：
  - `Get-Command ffmpeg` 失败
  - `winget list --id Gyan.FFmpeg.Essentials` 显示机器上其实已经安装 `FFmpeg (Essentials Build) 8.1`
- 继续在 WinGet 安装目录中定位到真实可执行文件：
  - `C:\Users\wxw\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe`
- 用该 `ffmpeg.exe` 验证了一个公开测试 HLS 源可读。
- 在当前仓库工作区启动 `client/main.py`，确认客户端能够成功初始化本地数据目录。
- 随后在临时工作区 `tmp_bl002_record_smoke/` 跑了一段更贴近任务页行为的 smoke：
  - 用 `TaskViewModel.save_task()` 新增 1 条直链 `m3u8` 任务并保存到本地
  - 用 `RecordManager.start_task()` 启动真实录制
  - 等待 8 秒后确认任务仍在 `running`
  - 用 `RecordManager.stop_task()` 停止任务
  - 校验录制文件与 `history.json` 已落盘
- 最后追加了打包版 `EXE` 验收：
  - 启动 `dist/DouyinLiveRecorder Client/DouyinLiveRecorder Client.exe`
  - 15 秒后确认进程仍存活、`Responding = true`
  - 确认打包版 `client_data/runtime_state.json` 已刷新
  - 验收后手动停止打包版进程

## 关键命令
```powershell
winget list --id Gyan.FFmpeg.Essentials
& 'C:\Users\wxw\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe' -version
& 'C:\Users\wxw\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe' -y -v error -t 5 -i 'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8' -f null -
Start-Process '.\.client-conda-env\python.exe' 'client\main.py'
& '.\.client-conda-env\python.exe' -  # 内联 smoke 脚本，执行 save_task / start_task / stop_task
Start-Process 'dist\DouyinLiveRecorder Client\DouyinLiveRecorder Client.exe'
```

## 已确认结果
- `ffmpeg` 真实版本：
  - `ffmpeg version 8.1-essentials_build-www.gyan.dev`
- `client/main.py` 启动后，真实工作区 `client_data/` 已生成：
  - `config.json`
  - `tasks.json`
  - `runtime_state.json`
  - `storage_meta.json`
  - `client.db`
- `client_data/runtime_state.json` 记录：
  - `hidden_to_tray = true`
  - `scheduler_running = true`
  - 说明客户端主窗口 / 托盘 / 调度链路至少成功运行过一次
- 临时工作区 `tmp_bl002_record_smoke/` 的录制链路结果：
  - `save_task` 成功，生成 `task-001`
  - `start_task` 成功，任务状态进入 `running`
  - 8 秒后 `running_after_sync = true`
  - `stop_task` 成功，最终状态 `stopped`
  - 录制文件：
    - `tmp_bl002_record_smoke/downloads/BL002_Smoke_Stream/BL002_Smoke_Stream_2026-04-01_23-25-27.ts`
  - 文件大小：
    - `332572` bytes
  - 历史记录：
    - `tmp_bl002_record_smoke/client_data/history.json` 记录数 = `1`
    - 状态 = `stopped`
    - 平台 = `direct`
- 打包版 `EXE` 验收结果：
  - `dist/DouyinLiveRecorder Client/DouyinLiveRecorder Client.exe` 启动后，进程数 = `1`
  - 进程名 = `DouyinLiveRecorder Client.exe`
  - 进程状态 = `Responding = true`
  - `dist/DouyinLiveRecorder Client/client_data/runtime_state.json` 时间戳发生更新
  - 打包版 `client_data/` 中已存在：
    - `client.db`
    - `config.json`
    - `runtime_state.json`
    - `storage_meta.json`
    - `tasks.json`
  - 打包版 `history.json` 仍未生成，这与源码入口一致：只有真正录制过后才会落盘

## 本次未完成
- 还没有通过 GUI 手工点击完成“新增任务 / 右键菜单 / 行内按钮 / 状态高亮 / 日志页联动 / 历史页刷新”的全链路观察。
- 还没有在打包版 `EXE` 中人工点过一轮真实任务创建与录制。

## 发现的问题
- 已确认：`ffmpeg` 已装，但当前 shell PATH 未自动生效；如果直接跑 `Get-Command ffmpeg` 会误判缺依赖。
- 已确认：真实工作区 `client_data/history.json` 与打包版 `client_data/history.json` 都不会在“仅启动客户端”时自动生成；需要录制链路真正跑过后才会落盘。

## 结论
- `BL-002` 已完成“仓库内源码入口 + 服务层录制链路 + 打包版 EXE 启动链路”的三段烟测。
- 从工程链路角度，`BL-002` 已基本闭环。
- 若没有必须保留的发布前人工 GUI 观察要求，可以把主要精力转入 `BL-004`。
