# 客户端发布与打包

最后更新：2026-03-31

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

## 后续可继续补强

- 增加 CI 构建工作流，自动产出 release zip
- 将变更摘要 / Release Notes 也纳入脚本生成流程
- 根据需要补充安装器或便携版清单
