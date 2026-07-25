# 2026-04-02 BL-004 NAS 首次真实部署尝试

## 本次做了什么
- 在用户已把公钥安装到 NAS `admin` 用户 `authorized_keys` 后，继续推进 `BL-004` 的真实主机验收。
- 验证了 SSH、远端 Python 和 Docker 版本。
- 直接执行了一次真实 `first-deploy`，并定位了新的实际阻塞点。
- 同时修复了 Windows 本机通过 SSH stdin 传远端 shell 脚本时的 CRLF 换行问题。

## 已确认
- SSH 已打通：
  - `ssh -i C:\Users\wxw\.ssh\id_ed25519_192_168_5_41 admin@192.168.5.41 "echo SSH_OK && whoami && uname -a"`
  - 返回：
    - `SSH_OK`
    - `admin`
    - `Linux Nas1 6.12.18-trim ... x86_64 GNU/Linux`
- 远端环境已确认：
  - `docker --version` = `Docker version 28.5.2, build ecc6942`
  - `docker compose version` = `Docker Compose version v2.40.3`
  - `python3 --version` = `Python 3.11.2`
  - `admin` 可写 `/vol1/docker`
  - `mkdir -p /vol1/docker/douyin-live-recorder` 返回 `MKDIR_OK`
- 本地真实部署命令已执行：
  - `& '.\.client-conda-env\python.exe' -m client.infra.docker.flyinnas_deploy --host 192.168.5.41 --user admin --scenario first-deploy --repo-root . --identity-file C:\Users\wxw\.ssh\id_ed25519_192_168_5_41`
- 首次执行时命中工具链问题：
  - 远端返回 `sh: 2: set: Illegal option -`
  - 已确认原因是 Windows 本机把通过 stdin 送给 SSH 的 shell 脚本换行转成了 CRLF，导致远端 `/bin/sh` 把 `set -eu\r` 识别坏掉
  - 已修复 `client/infra/docker/flyinnas_deploy.py`，改为用 UTF-8 字节流并强制保留 LF
  - 已补测试：`client/tests/test_flyinnas_deploy.py`
  - 已通过：
    - `& '.\.client-conda-env\python.exe' -m unittest client.tests.test_flyinnas_deploy -v`
    - `& '.\.client-conda-env\python.exe' -m py_compile client\infra\docker\flyinnas_deploy.py client\tests\test_flyinnas_deploy.py`

## 当前新的阻塞点
- 修复 CRLF 后再次执行真实 `first-deploy`，失败点已前移到远端 Docker 权限：
  - `permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock`
- 远端进一步探测结果：
  - `ls -l /var/run/docker.sock` = `srw-rw---- 1 root docker ... /var/run/docker.sock`
  - `getent group docker` = `docker:x:994:`
  - `groups` = `Users Administrators`
  - `sudo -n docker --version` 返回 `sudo: a password is required`

## 推断
- 当前不是 Docker 未安装，也不是部署脚本损坏，而是 `admin` 用户尚未加入 `docker` 组，且当前 SSH 自动化链路不能无密码 sudo。
- 一旦 `admin` 获得 Docker daemon 访问权限，现有部署脚本就可以继续复用，不需要再改部署流程。

## 待确认
- `admin` 是否能通过 `sudo usermod -aG docker admin` 或 NAS 图形界面方式加入 `docker` 组。
- 重新登录后，`groups` 是否出现 `docker`。
- 权限修正后，真实 `first-deploy` / `upgrade-deploy` / `rollback-deploy` 是否都能跑通。

## 下一次继续建议先做
1. 在 NAS 上把 `admin` 加入 `docker` 组。
2. 重新登录 SSH 会话。
3. 验证：
   - `groups`
   - `docker ps`
4. 再重新执行真实 `first-deploy`。
