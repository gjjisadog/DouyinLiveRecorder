# 2026-04-02 NAS SSH 认证补探

## 本次做了什么
- 基于用户提供的 NAS 信息 `192.168.5.41` / `admin`，继续推进 `BL-004` 的真实主机验收前置检查。
- 复核了本机 `~/.ssh` 目录，确认当前只有这次为 NAS 生成的专用密钥对。
- 用该私钥直接探测真实 NAS 的 SSH 登录结果，确认阻塞点落在“认证未通过”而不是“网络不通”。

## 已确认
- 本机存在 NAS 专用密钥对：
  - 私钥：`C:\Users\wxw\.ssh\id_ed25519_192_168_5_41`
  - 公钥：`C:\Users\wxw\.ssh\id_ed25519_192_168_5_41.pub`
- 公钥内容：
  - `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIN4YLmAgRgr0ug9Jk/GGe/hfj+6l8wnYEmGFAZTyYDiX admin@192.168.5.41`
- 公钥指纹：
  - `SHA256:yIQOknr0I9WrAqrDtxysgjewuUMjM3qumq5okgIFAm0`
- 探测命令：
  - `ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=publickey -i C:\Users\wxw\.ssh\id_ed25519_192_168_5_41 admin@192.168.5.41 "echo SSH_OK && whoami && uname -a"`
- 返回结果：
  - `Permission denied (publickey,password)`

## 推断
- 真实 NAS 主机当前网络和 SSH 端口是可达的，`BL-004` 的主要阻塞点已经收敛到“SSH 认证资料未就位”。
- 更具体地说，最可能缺的是把 `id_ed25519_192_168_5_41.pub` 追加到 NAS 上 `admin` 用户的 `authorized_keys`，或者 NAS 当前未允许该账号使用预期的认证方式。

## 待确认
- NAS 是否允许 `admin` 通过 SSH 登录。
- NAS 上 `admin` 的 `authorized_keys` 路径与权限是否正确。
- 安装公钥后，`docker --version`、`docker compose version` 以及 `deploy_flyinnas.ps1` 是否都能在真实主机上跑通。

## 下一次继续建议先做
1. 先把上面的公钥安装到 NAS 的 `admin` 用户 `authorized_keys`。
2. 再执行：
   - `ssh -i C:\Users\wxw\.ssh\id_ed25519_192_168_5_41 admin@192.168.5.41 "echo SSH_OK && whoami && uname -a"`
3. SSH 通后继续执行：
   - `ssh -i C:\Users\wxw\.ssh\id_ed25519_192_168_5_41 admin@192.168.5.41 "docker --version && docker compose version"`
4. 再按 `DOCKER_FLYINNAS.md` 跑真实 `first-deploy` / `upgrade-deploy` / `rollback-deploy`。
