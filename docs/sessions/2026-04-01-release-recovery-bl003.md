# 2026-04-01 Release Recovery BL-003

## 本次做了什么
- 从 `docs/handover/executable_backlog.md` 接手 `BL-003`“发布说明 / Release Notes 收口”。
- 核对了客户端发布相关文件：
  - `CLIENT_RELEASE.md`
  - `client/build_release.py`
  - `client/version.py`
  - `build_client_release.ps1`
  - `build_client_release.bat`
- 核对了现有发布产物：
  - `dist/DouyinLiveRecorder Client/`
  - `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.zip`
  - `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.sha256`
  - `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.manifest.json`
  - `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.manifest.md`
- 重新执行 `client.tests.test_build_release`，确认发布脚本相关回归 `10` 项通过。
- 执行 `client.build_release --dry-run`，确认当前 PyInstaller 命令、资源打包与 DLL 收集策略仍可被恢复。
- 将“当前可恢复的发布信息 / 无法仅靠本仓库恢复的发布信息”补写回 `CLIENT_RELEASE.md` 与 handover。

## 关键命令
```powershell
& '.\.client-conda-env\python.exe' -m unittest client.tests.test_build_release -v
& '.\.client-conda-env\python.exe' -m client.build_release --python '.\.client-conda-env\python.exe' --repo-root . --dry-run
```

## 已确认结果
- 版本入口仍清晰：
  - `client/version.py` = `4.0.7`
- 当前发布入口仍清晰：
  - `build_client_release.ps1`
  - `build_client_release.bat`
  - `client.build_release`
- 当前可直接从仓库恢复的发布信息包括：
  - 版本号
  - PyInstaller 构建命令
  - 目录版 / zip / checksum / manifest 产物命名规则
  - 当前 `dist/` 中的实际产物
  - 当前 `sha256` 与 manifest 内容
- `client.tests.test_build_release` 结果：
  - `Ran 10 tests`
  - `OK`
- 现有 manifest 可直接给出当前产物摘要：
  - 生成时间：`2026-03-31T19:51:54`
  - 平台：`windows-x64`
  - zip：`DouyinLiveRecorder-Client-4.0.7-windows-x64.zip`
  - exe：`DouyinLiveRecorder Client.exe`

## 待确认 / 无法仅靠仓库恢复
- 历史 Release 页面最终采用过哪一版文案
- 历史发布时是否都上传过 zip / checksum / manifest
- 历次人工验收记录是否完整保留
- 基于 Git 历史自动生成的 changelog

## 结论
- `BL-003` 已完成：当前发布链路的“仓库内可恢复部分”已经收口。
- 当前最重要的边界是：
  - **可以恢复**：当前版本如何打包、会产出什么、当前校验值是什么
  - **不能伪造**：历史 Release Notes 全量演进过程
- 后续如果要继续补发布记忆，应优先寻找外部 Git / Release 页面证据，而不是从本地仓库硬猜历史。
