# 2026-04-03 BL-014 按大小切段修复与复验

## 这次做了什么
- 修复分段模式下按文件大小自动切段失效的问题。
- 修复历史记录写入模板路径 `..._%03d.ts` 的问题。
- 重新打包客户端 EXE，并用同一条小阈值观察链路做真实复验。

## 修改点
- `client/core/ffmpeg_service.py`
  - 新增模板路径解析能力
  - `is_session_over_size_limit()` 改为对实际分段文件做大小判断
- `client/core/record_worker.py`
  - 在停止、完成、失败、自动切段前同步实际输出文件路径
- `client/tests/test_core_services.py`
  - 补回归测试：
    - 分段模板路径大小检测
    - 停止时把模板路径同步为实际输出路径

## 本地回归
```powershell
.\.client-conda-env\python.exe -m py_compile client/core/ffmpeg_service.py client/core/record_worker.py client/tests/test_core_services.py
.\.client-conda-env\python.exe -m unittest client.tests.test_core_services
```

结果：
- 语法检查通过
- `14` 项测试通过

## 重新打包
```powershell
.\.client-conda-env\python.exe -m client.build_release --python '.\.client-conda-env\python.exe' --repo-root .
```

结果：
- PyInstaller 真实构建成功
- `dist/DouyinLiveRecorder Client/DouyinLiveRecorder Client.exe` 已更新

## 打包版真实复验
```powershell
.\.client-conda-env\python.exe scripts/exe_automation_acceptance.py `
  --workspace tmp_bl014_rollover_fix_validation `
  --display-name BL014_Rollover_Fix `
  --record-seconds 20 `
  --max-file-size-gb 0.0002 `
  --poll-interval 1.0 `
  --command-timeout 25
```

## 关键产物
- 摘要：`tmp_bl014_rollover_fix_validation/acceptance_summary.json`

## 已确认事实
- 20 秒录制内自动切出了 3 段。
- `rollover_detected=true`
- 历史记录条数从 1 增长到 3。
- 历史记录中的 `file_path` 已是实际文件路径：
  - `..._09-23-48_000.ts`
  - `..._09-23-55_000.ts`
  - `..._09-24-02_000.ts`
- 录制日志里已出现两次：
  - “录制文件已达到单文件上限，准备自动切换新文件”
  - “已自动切换到新的录制文件”

## 当前边界观察
- 阈值：`214748` bytes
- 3 段文件大小分别约：
  - `350620`
  - `350996`
  - `350996`
- 当前最大超限偏差：`136248` bytes

## 结论
- `BL-014` 已完成，真实打包链路下的按大小自动切段已恢复可用。
- 当前仍不是“严格不超过阈值”的硬切段，而是“检测到超限后切到下一段”的实现。

## 后续建议
1. 如果需要更贴近 1GB 场景，再补一轮更长时间真实观察。
2. 如果需要更严格的阈值控制，再评估降低轮询间隔或引入更细粒度的文件大小监测。
