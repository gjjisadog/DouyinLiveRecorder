# 2026-04-05 BL-023 第二条外部长时真实 1GB 样本尝试

## 本次做了什么
- 为 `BL-023` 尝试寻找第二条可跑到真实 `1 GB` 的外部源。
- 期间顺手补了两类阻塞这条路径的代码问题：
  - 文件桥 JSON 读写加原子写入与脚本端重试
  - 带 query 的直链 HLS 从 `unknown` 改为正确识别为 `direct`
- 重新执行 `build_client_release.ps1`，把修正带进新打包版 EXE。

## 已确认可用候选
- `23 ABC / Uplynk`
  - `https://content-aaps1.uplynk.com/channel/ff809e6d9ec34109abfb333f0d4444b5/e.m3u8?pbs=e04cf259abd74d78974428201d237b41`

## 短样本

```powershell
& '.\.client-conda-env\python.exe' scripts\exe_automation_acceptance.py --repo-root . --workspace .\tmp_bl023_external_uplynk_probe2 --stream-url "https://content-aaps1.uplynk.com/channel/ff809e6d9ec34109abfb333f0d4444b5/e.m3u8?pbs=e04cf259abd74d78974428201d237b41" --display-name BL023_External_23ABC_Probe --record-seconds 120 --max-file-size-gb 1.0 --split-seconds 86400 --poll-interval 10 --log-limit 100
```

- 产物：`tmp_bl023_external_uplynk_probe2/acceptance_summary.json`
- 结果：
  - `success = true`
  - `120s` 产物大小：`29022500` bytes

## 长样本尝试

```powershell
& '.\.client-conda-env\python.exe' scripts\exe_automation_acceptance.py --repo-root . --workspace .\tmp_bl023_external_real_1gb_run2 --stream-url "https://content-aaps1.uplynk.com/channel/ff809e6d9ec34109abfb333f0d4444b5/e.m3u8?pbs=e04cf259abd74d78974428201d237b41" --display-name BL023_External_23ABC_1GB --record-seconds 5100 --max-file-size-gb 1.0 --split-seconds 86400 --poll-interval 15 --log-limit 200
```

- 产物：`tmp_bl023_external_real_1gb_run2/acceptance_summary.json`
- 中断前单段文件大小：`591921152` bytes
- 中断原因：
  - 脚本读取 `client_data/automation/response.json` 时命中 Windows 文件锁

## 当前结论
- `23 ABC / Uplynk` 现在已经能被新打包版按 `direct` 正常录制。
- 但该源在当前时段的真实落盘速率明显低于 playlist 标称码率，`5100s` 仍不足以稳定跑到 `1 GB`。
- `BL-023` 尚未完成，若继续沿该源推进，需要更长录制窗口；脚本侧的 `PermissionError` 重试已补上，可直接在此基础上继续。
