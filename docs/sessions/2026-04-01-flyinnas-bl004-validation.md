# 2026-04-01 FlyInNAS BL-004 Validation

## 本次做了什么
- 从 `docs/handover/executable_backlog.md` 接手 `BL-004`“飞牛云 / NAS 主机实跑回归”。
- 重新核对了 `DOCKER_FLYINNAS.md`、`DOCKER_FLYINNAS_CHECKLIST.md`、`DOCKER_FLYINNAS_REGRESSION.md`、`client/infra/docker/flyinnas_deploy.py`、`client/infra/docker/flyinnas_regression.py`、`deploy_flyinnas.ps1`、`deploy_flyinnas.sh`。
- 执行 `client.tests.test_flyinnas_deploy` 与 `client.tests.test_flyinnas_regression`，确认本机部署脚本与回归脚本的单测共 `11` 项通过。
- 执行 Python 部署入口 dry-run，确认可生成 NAS 所需的 `scp` / `ssh` 命令。
- 执行 PowerShell 部署入口 dry-run，确认在 `powershell -ExecutionPolicy Bypass -File ...` 方式下可正确透传到 Python 模块。
- 接续上一轮已拉起的本机 Docker 容器，确认 `douyin-live-recorder` 状态为 `healthy`，并检查最近日志。
- 在本机依次执行：
  - `first-deploy`
  - `upgrade-deploy --expected-tag 4.0.7`
  - `rollback-deploy --expected-tag 4.0.7`
  三个回归场景，结果均为 `PASS`。
- 验证完成后执行 `docker compose -f docker-compose.flyinnas.yaml down --remove-orphans`，并恢复 `config/URL_config.ini` 原内容。

## 关键命令
```powershell
& '.\.client-conda-env\python.exe' -m unittest client.tests.test_flyinnas_deploy client.tests.test_flyinnas_regression -v
& '.\.client-conda-env\python.exe' -m client.infra.docker.flyinnas_deploy --host nas.local --user admin --scenario rollback-deploy --expected-tag 4.0.7 --repo-root . --dry-run
powershell -ExecutionPolicy Bypass -File .\deploy_flyinnas.ps1 -RemoteHost nas.local -User admin -Scenario rollback-deploy -ExpectedTag 4.0.7 -DryRun
docker compose -f docker-compose.flyinnas.yaml ps
docker inspect --format='{{json .State.Health}}' douyin-live-recorder
docker compose -f docker-compose.flyinnas.yaml logs --tail=200
& '.\.client-conda-env\python.exe' -m client.infra.docker.flyinnas_regression first-deploy --app-root .
& '.\.client-conda-env\python.exe' -m client.infra.docker.flyinnas_regression upgrade-deploy --app-root . --expected-tag 4.0.7
& '.\.client-conda-env\python.exe' -m client.infra.docker.flyinnas_regression rollback-deploy --app-root . --expected-tag 4.0.7
docker compose -f docker-compose.flyinnas.yaml down --remove-orphans
```

## 已确认结果
- 单测结果：
  - `Ran 11 tests in 0.042s`
  - `OK`
- Python dry-run 结果：
  - 可输出目标包 `douyin-live-recorder-flyinnas-4.0.7.tar.gz`
  - 可输出预期 `scp` / `ssh` 命令
- PowerShell dry-run 结果：
  - 在 `ExecutionPolicy Bypass` 下可输出与 Python 模块一致的 `scp` / `ssh` 命令
- 本机容器状态：
  - `douyin-live-recorder` 为 `Up ... (healthy)`
  - 健康检查返回 `recorder healthy with 1 configured target(s)`
- 本机三组回归结果：
  - `Scenario: first-deploy` → `Result: PASS`
  - `Scenario: upgrade-deploy` → `Result: PASS`
  - `Scenario: rollback-deploy` → `Result: PASS`
  - 三组结果均确认：
    - `container_state: state=running`
    - `container_health: health=healthy`
    - `container_image: image=douyin-live-recorder:4.0.7`
- 验证收尾：
  - 已执行 `docker compose down --remove-orphans`
  - 已恢复 `config/URL_config.ini` 原内容

## 本次未完成
- 还没有在真实 NAS / 飞牛云宿主机执行一次完整的：
  - `docker compose up -d --build`
  - `first-deploy`
  - `upgrade-deploy`
  - `rollback-deploy`
- 还没有拿到宿主机侧的挂载、网络、权限、截图与命令输出证据。

## 发现的问题
- 已确认：PowerShell 直接执行 `.\deploy_flyinnas.ps1 ...` 可能受当前会话执行策略影响；这更像环境限制，不是脚本逻辑错误。
- 已确认：`deploy_flyinnas.ps1` 的主机参数名是 `-RemoteHost`，不是 `-Host`；调用示例需要保持一致，避免误传参。

## 结论
- `BL-004` 已完成“仓库内可验证部分”的收口：
  - 单测通过
  - 部署 dry-run 通过
  - 本机容器健康检查通过
  - 本机三种回归场景通过
- 目前 `BL-004` 的剩余工作已明确收敛为“真实 NAS / 飞牛云宿主机实跑并补证据”。
- 如果短期内无法访问宿主机，下一项最适合继续推进的仓库内任务是 `BL-005`。
