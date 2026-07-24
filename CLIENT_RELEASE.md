# 客户端发布与打包

最后更新：2026-04-05

## 当前产物目标

- Windows 桌面客户端可通过 PyInstaller 打包为独立目录版。
- 打包过程具备统一版本号、版本信息文件、资源目录打包和图标资源。
- 仓库内保留清晰的本地发布流程，便于后续接 CI。

## 当前验证状态

- `2026-03-31` 已重新执行 `& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v`，共 `65` 项客户端测试全部通过。
- `2026-03-31` 已重新执行 `& '.\.client-conda-env\python.exe' -m client.build_release --python '.\.client-conda-env\python.exe' --repo-root '.'`，PyInstaller 真实打包成功，且已自动生成压缩包、SHA256 校验清单与发布清单。
- 当前产物目录为 `dist/DouyinLiveRecorder Client/`，主程序为 `dist/DouyinLiveRecorder Client/DouyinLiveRecorder Client.exe`。
- 当前发布产物额外包括：
  - `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.zip`
  - `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.sha256`
  - `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.manifest.json`
  - `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.manifest.md`
- `2026-03-31` 已完成一次正式 `dist` 产物冷启动冒烟，主窗口标题为 `DouyinLiveRecorder Client 4.0.7`，窗口响应正常。
- 首次冷启动已写出 `client.db`、`config.json`、`storage_meta.json`、`tasks.json`；`history.json` 仍按首次写入历史记录时再创建。
- 构建期间的已知 warning 已写入 `build/client-release/work/DouyinLiveRecorder Client/warn-DouyinLiveRecorder Client.txt`，当前视为 conda + PyInstaller 下的已知告警噪音。
- 当前宿主机未安装真实 `ffmpeg`，本轮通过临时 `ffmpeg` stub 绕过依赖确认提示，仅验证窗口级启动与首次初始化。
- 仍建议在正式发版前补一轮首页、设置页、任务页、历史页、日志页和托盘的人工点点点检查，以及安装真实 `ffmpeg` 后的录制链路冒烟。

## 发布前验收收口（2026-04-05）

### 已确认可作为发布前证据

- 打包版主程序：
  - `dist/DouyinLiveRecorder Client/DouyinLiveRecorder Client.exe`
  - 已确认可真实启动并完成自动化桥接验收
- `BL-019` 真实 `1 GB` 按大小切段验收：
  - 证据文件：`tmp_bl019_local_source_1gb_run1/acceptance_summary.json`
  - 验收方式：本地连续 HLS 源 + 打包版 EXE + `direct m3u8`
  - 结果：
    - `success = true`
    - `rollover_detected = true`
    - 共 3 段文件
    - 段大小：
      - `1073444092`
      - `1075609664`
      - `645593504`
    - 阈值：`1073741824` bytes
    - `max_overshoot_bytes = 1867840`
    - 最大超限占比约 `0.17%`
    - 录制日志已出现两次“录制文件已达到单文件上限，准备自动切换新文件”
  - 当前发布决策：
    - 接受当前 `1 MB` 安全余量结果
    - 不再继续微调阈值策略
- `BL-017` 打包版 `get_logs` 稳定性验收：
  - 证据文件：
    - `tmp_bl017_get_logs_stability_run1/acceptance_summary.json`
    - `tmp_bl017_get_logs_stability_run3/acceptance_summary.json`
    - `tmp_bl017_get_logs_stability_run4/acceptance_summary.json`
  - 汇总结果：
    - 累计 `105/105` 次 `get_logs` 调用成功
    - 未复现 `BL-013` 中的超时
    - 常态响应约 `200ms`
    - 部分轮次约 `400ms`
    - 已观测最大延迟 `406.09ms`
- `BL-020` 外部长时源对照样本：
  - 证据文件：`tmp_bl020_external_control_abc_run1/acceptance_summary.json`
  - 对照源：`https://abcnews-streams.akamaized.net/hls/live/2023566/abcnewshudson7/master_4000.m3u8`
  - 验收口径：外部新闻直播流、`0.01 GB` 阈值、`600s` 长样本
  - 结果：
    - `success = true`
    - `rollover_detected = true`
    - 前 3 段大小：
      - `9744604`
      - `9750808`
      - `9776000`
    - `max_overshoot_bytes = 0`
  - 价值：
    - 说明当前切段链路不只在本地自建连续流下有效
    - 在更接近真实业务流的外部长时样本中，同样未出现“未达阈值先自然结束再重拉”的问题
- `BL-021` 外部长时真实 `1 GB` 全量样本：
  - 证据文件：`tmp_bl021_external_real_1gb_run1/acceptance_summary.json`
  - 样本源：`https://live.corusdigitaldev.com/groupb/live/3062d0e3-ed4c-4f47-8482-95648250f4b8/live.isml/live-audio_1=96000-video=2499968.m3u8`
  - 启动时间：`2026-04-04 23:22:34`
  - 首次按大小切段时间：`2026-04-05 00:18:00`
  - 停止时间：`2026-04-05 00:37:35`
  - 验收口径：外部长时公开新闻直播流、真实 `1 GB` 阈值、`4500s` 长样本
  - 结果：
    - `success = true`
    - `rollover_detected = true`
    - 共 2 段文件
    - 第一段大小：`1072987252`
    - 第二段大小：`392916052`
    - 阈值：`1073741824` bytes
    - `max_overshoot_bytes = 0`
    - 历史记录中第一段状态为 `completed`，第二段状态为测试结束后的 `stopped`
    - 录制日志明确出现“录制文件已达到单文件上限，准备自动切换新文件”
  - 价值：
    - 已补齐此前仍缺的“外部长时真实 `1 GB` 全量样本”
    - 说明打包版客户端在公开外部长时源下，也能真实跑到 `1 GB` 并完成按大小自动切段
- `BL-022` 外部源 `get_logs` 对照样本：
  - 证据文件：`tmp_bl022_external_get_logs_run1/acceptance_summary.json`
  - 样本源：`https://live.corusdigitaldev.com/groupb/live/3062d0e3-ed4c-4f47-8482-95648250f4b8/live.isml/live-audio_1=96000-video=2499968.m3u8`
  - 验收口径：外部公开新闻直播流、`300s` 样本、`1s` 查询间隔
  - 结果：
    - `success = true`
    - `total_calls = 240`
    - `successful_calls = 240`
    - `failed_calls = 0`
    - `max_latency_ms = 404.22`
    - `avg_latency_ms = 250.36`
  - 价值：
    - 已补齐此前只基于本地连续流的 `get_logs` 稳定性证据
    - 说明外部源录制过程中，文件桥下的 `get_logs` 同样稳定

### 当前仍保留的边界

- 公网 Mux 测试流样本 `tmp_bl019_real_1gb_run2/` 已确认不适合作为最终依据，因为流会在未达到 `1 GB` 前自然结束并被重新拉起。
- `BL-021` 已补齐一条外部长时真实 `1 GB` 证据，但当前外部 `1 GB` 背书仍主要来自单一公开新闻源，不等价于“所有外部源都已覆盖”。
- `BL-022` 已补齐一条外部源 `get_logs` 对照样本，但当前外部 `get_logs` 背书仍主要来自单一公开新闻源。
- 因此当前仓库能明确给出的结论是：
  - 打包版客户端的 `1 GB` 自动切段链路已在可控本地长时源下通过
  - 打包版客户端的 `1 GB` 自动切段链路也已在公开外部长时新闻流下通过
  - 外部长时新闻流样本已在 `0.01 GB` 阈值下通过稳定切段对照
  - `get_logs` 在当前文件桥路径下已在本地连续流和外部公开新闻流两条样本上稳定
  - 若后续还要继续补强，只剩“更多外部源的 `1 GB` 全量样本”或“外部源 `get_logs` 对照样本”这类增强证据

## 当前可恢复的发布信息（2026-04-01 复核）

- 已确认可直接从仓库恢复：
  - 版本号：`client/version.py`
  - 本地打包入口：`build_client_release.ps1`、`build_client_release.bat`
  - 打包实现：`client/build_release.py`
  - 发布产物命名规则：`DouyinLiveRecorder-Client-4.0.7-windows-x64.*`
  - 当前 `dist/` 产物、`manifest.json`、`manifest.md`、`sha256`
  - 打包相关自动化回归：`client/tests/test_build_release.py`
- 已确认当前 `dist/` 中仍可核对：
  - `dist/DouyinLiveRecorder Client/`
  - `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.zip`
  - `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.sha256`
  - `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.manifest.json`
  - `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.manifest.md`
- 待确认 / 无法仅靠当前仓库恢复：
  - 对外发布时实际采用过哪一版文案
  - 历史 Release 页面是否上传过这些产物
  - 每次发布对应的人工验收记录是否完整
  - 基于 Git 历史自动生成的 changelog
- 结论：
  - 当前仓库足以恢复“怎么打包、产出什么、当前产物校验值是什么”
  - 但**不足以**恢复“完整历史 Release Notes 演进过程”

## 版本与资源

- 统一版本入口：`client/version.py`
- 应用设置：`client/app_settings.py`
- 图标资源：`client/resources/app_icon.svg`
- Windows 版本文件：由 `client/build_release.py` 在构建时生成到 `build/client-release/windows-version-info.txt`

## 构建依赖

```powershell
& '.\.client-conda-env\python.exe' -m pip install -r requirements.client-build.txt
```

## 本地打包

PowerShell:

```powershell
.\build_client_release.ps1
```

批处理:

```bat
build_client_release.bat
```

直接调用构建模块:

```powershell
& '.\.client-conda-env\python.exe' -m client.build_release --python '.\.client-conda-env\python.exe' --repo-root .
```

只执行 PyInstaller 命令解析、不落地产物:

```powershell
& '.\.client-conda-env\python.exe' -m client.build_release --python '.\.client-conda-env\python.exe' --repo-root . --dry-run
```

只构建目录版、跳过 zip / 校验和 / 清单生成:

```powershell
& '.\.client-conda-env\python.exe' -m client.build_release --python '.\.client-conda-env\python.exe' --repo-root . --skip-package
```

## 产物目录

- `dist/DouyinLiveRecorder Client/`
- `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.zip`
- `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.sha256`
- `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.manifest.json`
- `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.manifest.md`
- 构建中间文件：`build/client-release/`

## 当前打包策略

- 使用 `PyInstaller`
- `--windowed`
- 自动收集 `PySide6` 与 `shiboken6`
- 额外收集 conda `Library/bin` 运行时 DLL，补齐 PySide6 / Shiboken / Qt 动态库依赖
- 自动将 `client/resources` 打进包内
- Windows 下自动生成版本信息文件
- 自动将 `client/resources/app_icon.ico` 作为 exe 图标嵌入
- 构建完成后自动将目录版压缩为版本化 zip
- 自动输出 `sha256` 校验清单，覆盖 zip、exe 与两份 manifest
- 自动输出机器可读 JSON 清单与便于人工核对的 Markdown 清单

## 发布清单说明

- `*.zip`：正式分发压缩包，解压后包含 `DouyinLiveRecorder Client/` 根目录。
- `*.sha256`：校验和清单，默认包含 zip、exe、manifest.json、manifest.md 四类发布文件的 SHA256。
- `*.manifest.json`：机器可读发布清单，包含版本号、平台、生成时间、目录内文件列表、文件数、总大小和发布产物摘要。
- `*.manifest.md`：人工可读发布清单，便于在 Release 页面、测试交付或归档时直接查看。

## 校验方式

使用 PowerShell 按 `sha256` 清单逐项校验：

```powershell
$dist = 'E:\Project\DouyinLiveRecorder-4.0.7\dist'
Get-Content (Join-Path $dist 'DouyinLiveRecorder-Client-4.0.7-windows-x64.sha256') | ForEach-Object {
    $parts = $_ -split ' \\*', 2
    $expected = $parts[0].Trim()
    $fileName = $parts[1].Trim()
    $actual = (Get-FileHash -Algorithm SHA256 (Join-Path $dist $fileName)).Hash.ToLower()
    [PSCustomObject]@{
        File = $fileName
        Expected = $expected
        Actual = $actual
        Match = ($expected -eq $actual)
    }
}
```

## 建议发布检查

1. 运行客户端测试：
   `& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v`
2. 运行构建脚本，确认 `dist/` 下同时生成目录版、zip、sha256、manifest.json、manifest.md。
3. 校验 `DouyinLiveRecorder-Client-4.0.7-windows-x64.sha256` 中各文件哈希值。
4. 启动 `dist` 中的客户端，确认首页、设置页、任务页、系统托盘和日志页可正常打开。
5. 检查 `client_data` 首次初始化是否会写出 `client.db`、`config.json`、`tasks.json`、`storage_meta.json`，以及历史功能首次写入时补出 `history.json`。
6. 验证 `ffmpeg` 缺失提示、任务导入导出、设置保存、通知测试与历史页加载。
7. 如需引用最新自动化验收结论，优先附上：
   - `tmp_bl019_local_source_1gb_run1/acceptance_summary.json`
   - `tmp_bl017_get_logs_stability_run3/acceptance_summary.json`

## 后续可继续补强

- 增加 CI 构建工作流，自动产出 release zip
- 将变更摘要 / Release Notes 也纳入脚本生成流程
- 根据需要补充安装器或便携版清单
