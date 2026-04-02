# 2026-04-02 Cleanup And BL-004 Follow-up

## 本次做了什么
- 在 `BL-008` 已建立首个恢复提交后，继续处理根目录两个权限异常孤儿目录：
  - `tmp7qf85p61/`
  - `tmpbape0idz/`
- 再次接手下一项 backlog：`BL-004` 飞牛云 / NAS 主机实跑回归。

## 权限异常目录处理结果
- 已确认这两个目录位于仓库根目录，`Get-Item` 识别为普通目录而非可见符号链接。
- 已尝试以下清理方式：
  - PowerShell `Remove-Item -Recurse -Force`
  - `takeown /f ... /r /d y`
  - `icacls ...`
  - `cmd /c rd /s /q ...`
  - `fsutil reparsepoint query ...`
- 已确认结果：
  - 所有路径都返回 `Access is denied`
  - 当前会话无法读取 ACL，也无法删除目录
- 推断：
  - 更像宿主机 ACL 或所有权异常，而不是普通空目录残留
  - 需要管理员权限会话或宿主机手工处理

## BL-004 跟进结果
- 已确认 `nas.local` 在当前机器上不可达：
  - `Test-Connection nas.local -Count 1 -Quiet` 返回 `False`
- 已再次执行三种场景 dry-run，确认部署工具链仍能稳定生成命令：
  - `first-deploy`
  - `upgrade-deploy`
  - `rollback-deploy`
- 本次 dry-run 产出（示例主机仍为 `nas.local`）：
  - `scp -P 22 ... admin@nas.local:/tmp/douyin-live-recorder-flyinnas-4.0.7.tar.gz`
  - `ssh -p 22 admin@nas.local sh -s -- /vol1/docker/douyin-live-recorder /tmp/douyin-live-recorder-flyinnas-4.0.7.tar.gz <scenario> python3 4.0.7 ''`

## 已确认
- `BL-008` 当前只剩 ACL 异常目录这一类本地环境尾项，不再阻塞 Git 基线本身。
- `BL-004` 的仓库内准备工作仍然完好；当前阻塞点不是脚本损坏，而是“缺真实 NAS 宿主机可达性与执行环境”。

## 待确认
- 是否能在管理员权限终端中删除 `tmp7qf85p61/`、`tmpbape0idz/`。
- 真实 NAS / 飞牛云宿主机的 SSH 地址、账号与挂载路径是否与文档示例一致。
- 宿主机上 `docker compose up -d --build`、`first-deploy`、`upgrade-deploy`、`rollback-deploy` 是否全部通过。

## 建议下一步
1. 在管理员权限终端删除两个 ACL 异常目录，并把结果补回 handover。
2. 拿到真实 NAS 宿主机后，按 `DOCKER_FLYINNAS.md`、`DOCKER_FLYINNAS_CHECKLIST.md`、`DOCKER_FLYINNAS_REGRESSION.md` 执行实机回归。
3. 若短期内拿不到 NAS 宿主机，切换到下一项可仓内闭环的 backlog，例如 `BL-002` GUI 手点验收或客户端平台补证。

## 管理员终端最小命令单
- 适用前提：
  - 以“管理员身份运行”的 PowerShell 或 Windows Terminal
  - 当前工作目录位于仓库根目录
- PowerShell 方案：
```powershell
Set-Location 'E:\Project\DouyinLiveRecorder-4.0.7'

takeown /f .\tmp7qf85p61 /r /d y
takeown /f .\tmpbape0idz /r /d y

icacls .\tmp7qf85p61 /grant "$env:USERNAME:(OI)(CI)F" /t /c
icacls .\tmpbape0idz /grant "$env:USERNAME:(OI)(CI)F" /t /c

Remove-Item .\tmp7qf85p61 -Recurse -Force
Remove-Item .\tmpbape0idz -Recurse -Force

git status --short --ignored
```
- 如果 PowerShell 中 `icacls` 参数仍然报错，可改用 `cmd` 版本：
```cmd
cd /d E:\Project\DouyinLiveRecorder-4.0.7
takeown /f tmp7qf85p61 /r /d y
takeown /f tmpbape0idz /r /d y
icacls tmp7qf85p61 /grant %USERNAME%:(OI)(CI)F /t /c
icacls tmpbape0idz /grant %USERNAME%:(OI)(CI)F /t /c
rd /s /q tmp7qf85p61
rd /s /q tmpbape0idz
git status --short --ignored
```
- 待确认：
  - 如果管理员终端中仍然 `Access is denied`，则问题更可能位于宿主机所有权 / ACL 继承链，而不是普通仓库残留目录。
