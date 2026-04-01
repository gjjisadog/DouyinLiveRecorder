# 当前可执行 Backlog

最后更新：2026-04-01

## 说明
- 本文件从 `CLIENT_TASK_TRACKER.md` 中提炼“当前还能继续执行”的事项，优先保留已能在仓库内落地验证的任务。
- 每项任务都尽量标明：`已确认`、`推断`、`待确认`。
- 如果某项已经在真实环境跑通，会移入“已完成（最近）”，避免重复开工。

## 已完成（最近）

### BL-001 Docker 实机构建验收
- 优先级：P0
- 状态：已完成（2026-04-01）
- 来源：`CLIENT_TASK_TRACKER.md` 的 Docker / NAS 收尾项、`D-001`
- 已确认
  - 当前机器已安装 `Docker 29.3.1` 与 `Docker Compose v5.1.0`。
  - 已执行 `docker compose -f docker-compose.flyinnas.yaml up -d --build`，镜像 `douyin-live-recorder:4.0.7` 构建成功。
  - 容器 `douyin-live-recorder` 已进入 `running` / `healthy`。
  - 健康检查返回 `recorder healthy with 1 configured target(s)`。
  - 已执行 `& '.\.client-conda-env\python.exe' -m client.infra.docker.flyinnas_regression first-deploy --app-root .`，结果为 `PASS`。
  - 验收后已执行 `docker compose -f docker-compose.flyinnas.yaml down --remove-orphans`，并把 `config/URL_config.ini` 恢复为原始内容。
- 本次补充
  - 为解决构建过程中的 Debian 源瞬时 `502 Bad Gateway`，已在 `Dockerfile` 中加入显式 `apt` 重试循环。
- 待确认
  - 仍需在真实 NAS / 飞牛云宿主机再跑一遍同样流程，确认宿主机网络和磁盘挂载行为一致。

### BL-002 客户端录制链路二轮人工冒烟
- 优先级：P0
- 状态：大部分已完成（仓库内 + `dist` 启动烟测已通过）
- 来源：`CLIENT_TASK_TRACKER.md` 当前建议推进顺序 #2，关联 `C-004`、`C-011`、`C-012`
- 已确认
  - `client/tests/` 已通过过一轮 76 项回归。
  - 桌面客户端主窗口、任务页、设置页、日志页、历史页、通知服务、托盘链路已经落地。
  - `winget list --id Gyan.FFmpeg.Essentials` 显示当前机器已安装 `FFmpeg (Essentials Build) 8.1`。
  - `ffmpeg.exe` 实际位于 `C:\Users\wxw\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe`。
  - `client/main.py` 可成功启动；真实工作区 `client_data/` 已生成：
    - `config.json`
    - `tasks.json`
    - `runtime_state.json`
    - `storage_meta.json`
    - `client.db`
  - 临时工作区 `tmp_bl002_record_smoke/` 中，已真实跑通：
    - `TaskViewModel.save_task()`
    - `RecordManager.start_task()`
    - 持续录制 8 秒
    - `RecordManager.stop_task()`
    - 录制文件与 `history.json` 均已落盘
  - `dist/DouyinLiveRecorder Client/DouyinLiveRecorder Client.exe` 已在 2026-04-01 再次真实拉起：
    - 进程存活且 `Responding = true`
    - `dist/DouyinLiveRecorder Client/client_data/runtime_state.json` 时间戳已更新
    - 打包版 `client_data/` 中已存在 `client.db`、`config.json`、`runtime_state.json`、`storage_meta.json`、`tasks.json`
- 当前剩余
  - 还没有通过 GUI 手工点击完整覆盖“新增任务 / 右键菜单 / 行内按钮 / 状态高亮 / 日志页联动 / 历史页刷新”。
  - 打包版 `EXE` 还没有人工点过一轮真实任务创建与录制。
- 备注
  - 从“能启动、能持久化、能录、能停”的工程链路角度看，`BL-002` 已经基本收口；剩余项主要是人工交互确认。

## 当前待执行

### BL-004 飞牛云 / NAS 主机实跑回归
- 优先级：P1
- 状态：部分完成（本机 dry-run / regression 已通过，待 NAS 实机）
- 来源：`CLIENT_TASK_TRACKER.md` 当前建议推进顺序 #4，关联 `D-001`
- 已确认
  - `DOCKER_FLYINNAS.md`、`DOCKER_FLYINNAS_CHECKLIST.md`、`DOCKER_FLYINNAS_REGRESSION.md` 与 `client.infra.docker.flyinnas_regression` 已齐备。
  - 本机 Windows Docker 已完成一次实构建验收。
  - `& '.\.client-conda-env\python.exe' -m unittest client.tests.test_flyinnas_deploy client.tests.test_flyinnas_regression -v` 已通过，结果为 `11 tests OK`。
  - `& '.\.client-conda-env\python.exe' -m client.infra.docker.flyinnas_deploy --host nas.local --user admin --scenario rollback-deploy --expected-tag 4.0.7 --repo-root . --dry-run` 可正确生成 `scp` / `ssh` 命令。
  - `powershell -ExecutionPolicy Bypass -File .\deploy_flyinnas.ps1 -RemoteHost nas.local -User admin -Scenario rollback-deploy -ExpectedTag 4.0.7 -DryRun` 可正确走通 PowerShell 入口并输出 `scp` / `ssh` 命令。
  - 在临时写入 README 公开示例地址后，本机已再次执行 `docker compose -f docker-compose.flyinnas.yaml up -d --build`，容器 `douyin-live-recorder` 达到 `healthy`。
  - `first-deploy`、`upgrade-deploy`、`rollback-deploy` 三个本机回归场景均已返回 `PASS`。
  - 验证收尾后已再次执行 `docker compose -f docker-compose.flyinnas.yaml down --remove-orphans`，并恢复 `config/URL_config.ini` 原内容。
- 待确认
  - NAS 宿主机上的 `docker compose up -d --build`、升级部署、回滚部署是否都能稳定通过。
- 建议动作
  1. 将当前仓库同步到 NAS / 飞牛云宿主机
  2. 准备真实 `config/URL_config.ini`
  3. 在宿主机执行 `docker compose up -d --build`、`first-deploy`、`upgrade-deploy`、`rollback-deploy`
  4. 把宿主机截图、命令输出和异常写回 `docs/sessions/`

### BL-005 平台接入覆盖复核
- 优先级：P1
- 状态：已完成（2026-04-01）
- 来源：`CLIENT_TASK_TRACKER.md`，关联 `C-002`
- 已确认
  - `client/core/platform_router.py` 与 `client/core/stream_resolver.py` 当前已接入 `13` 个客户端平台：抖音、TikTok、快手、虎牙、斗鱼、YY、B站、网易 CC、千度热播、PandaTV、百度直播、ShowRoom、CHZZK。
  - 客户端还支持自定义 `m3u8` / `flv` 直链录制。
  - README 主程序“已支持平台”列表当前共有 `51` 个平台；客户端接入范围明显更窄，不能直接等同。
  - `client/tests/test_platform_migration.py` 已确认：
    - 路由识别：网易 CC、千度热播、PandaTV、百度直播、ShowRoom、CHZZK
    - 解析分支：网易 CC、CHZZK
  - `client/tests/test_task_import_export.py`、`client/tests/test_task_viewmodel.py` 已确认任务导入 / 任务页 / 持久化链路覆盖：抖音、TikTok、快手、ShowRoom、CHZZK。
  - `client/tests/test_core_services.py` 已确认：
    - 抖音存在客户端 `ffmpeg` 选流相关回归
    - PandaTV 存在代理 / Header 构建回归
  - `docs/sessions/2026-04-01-client-bl002-smoke.md` 已确认自定义 `m3u8` 直链录制烟测通过。
- 推断
  - 虎牙、斗鱼、YY、B站虽然已存在客户端迁移分支，但当前仓库内仍缺客户端专用解析回归证据。
- 本次产出
  1. 已形成“代码接入范围 vs 自动化验证范围”的差异结论
  2. 已将客户端平台边界补写回 `README.md`
  3. 已把后续补测焦点收敛到“已接线但证据不足”的平台

### BL-006 配置示例与脱敏说明补齐
- 优先级：P1
- 状态：已完成（2026-04-01）
- 来源：`docs/handover/known_issues.md`
- 已确认
  - `config/config.ini` 当前确实包含真实风格的 Cookie / Token / 推送 / 账号字段，不能作为公开样板继续引用。
  - 已新增安全可提交的示例配置：
    - `config/config.example.ini`
    - `config/URL_config.example.ini`
  - `README.md` 已补充“示例配置使用方式”与“共享前先脱敏”的明确说明。
- 推断
  - 后续如果继续扩展平台或通知能力，示例配置也需要同步补字段，避免再次回退到“直接复制本地真实配置”的做法。
- 本次产出
  1. 已完成敏感字段盘点并确认高风险区在 `Cookie`、`Authorization`、`账号密码`、`推送配置`
  2. 已提供可直接复制的脱敏样板
  3. 已把配置脱敏规则补写回 README / handover

### BL-003 发布说明 / Release Notes 收口
- 优先级：P1
- 状态：已完成（2026-04-01）
- 来源：`CLIENT_TASK_TRACKER.md` 当前建议推进顺序 #3，关联 `C-011`
- 已确认
  - `client/build_release.py` 与 `CLIENT_RELEASE.md` 已存在。
  - `client/tests/test_build_release.py` 已通过，结果为 `10 tests OK`。
  - 当前 `dist/` 中可直接核对现有客户端发布产物：
    - `DouyinLiveRecorder Client/`
    - `DouyinLiveRecorder-Client-4.0.7-windows-x64.zip`
    - `DouyinLiveRecorder-Client-4.0.7-windows-x64.sha256`
    - `DouyinLiveRecorder-Client-4.0.7-windows-x64.manifest.json`
    - `DouyinLiveRecorder-Client-4.0.7-windows-x64.manifest.md`
  - `client.build_release --dry-run` 可稳定还原当前 PyInstaller 命令与 DLL 打包策略。
  - `CLIENT_RELEASE.md` 已补充“当前可恢复的发布信息”说明。
- 待确认
  - 当前仓库缺少可核对的 Git 历史，无法严谨恢复历史 Release Notes 演进过程。
- 本次产出
  1. 已确认哪些发布信息可从仓库直接恢复
  2. 已明确哪些信息只能等待外部 Release 页面或历史仓库补证
  3. 已将边界写回 `CLIENT_RELEASE.md` 与 handover

### BL-007 临时目录清理策略
- 优先级：P2
- 状态：已完成（2026-04-02）
- 来源：`docs/handover/known_issues.md`
- 已确认
  - 仓库根目录当前可见 `20` 个 `tmp*` 目录，其中：
    - `tmp_bl002_record_smoke` 含真实录制产物与 `history.json`，已被现有 session 文档引用，应默认视为取证目录
    - `tmp_config_log_*`、`tmp_history_*`、`tmp_notify_*`、`tmp_scheduler_*`、`tmp_settings_notify_*`、`tmp_task_store_log*` 更像测试 / 调试残留
    - `tmp7qf85p61`、`tmpbape0idz` 为空目录，且此前 `git status` 曾对其报权限告警
  - 已新增 `.gitignore` 规则：`tmp*/`
  - 已新增安全清理脚本：`scripts/cleanup_tmp_artifacts.ps1`
- 推断
  - 后续只要 session 文档仍引用某个 `tmp_*` 目录，该目录就不宜默认自动删除。
- 本次产出
  1. 已形成“session 引用即保留、未引用则候选清理”的策略
  2. 已补充根目录 `tmp*` 忽略规则
  3. 已提供默认 dry-run、可选删除的清理脚本

### BL-008 Git 状态基线恢复
- 优先级：P2
- 状态：部分完成（2026-04-02）
- 来源：`docs/handover/next_steps.md`
- 已确认
  - 当前 `git status --short` 近乎整仓未纳入版本控制，且存在若干无权限目录告警。
  - `.git/` 已存在，但当前无可读 branch / remote / commit 历史；更像“空仓库重新初始化”状态。
  - 已补充 `.gitignore`：
    - `client_data/`
    - `tmp_*.log`
    - 以及上一轮已加入的 `tmp*/`
  - 已形成“源码 / 文档 / 配置模板 / 脚本”与“运行产物 / 构建产物 / 临时目录”的边界分类，详见 `docs/sessions/2026-04-02-git-baseline-bl008.md`
- 待确认
  - 是否要在当前本地仓库直接建立“首个恢复提交”
  - `deploy/`、`tmp7qf85p61/`、`tmpbape0idz/` 这些孤儿项是否应先物理清理
- 下一步建议
  1. 先删除或确认孤儿目录
  2. 再按“源码 / 文档 / 模板 / 脚本”建立最小提交基线
  3. 之后再推进正常功能开发

## 当前优先顺序
1. `BL-004` 飞牛云 / NAS 主机实跑回归（仅剩宿主机验证）
2. `BL-008` Git 状态基线恢复（等待是否建立首个恢复提交）
3. 如需发布前人工确认，再补 `BL-002` GUI 手点验收
4. 如需继续补客户端平台证据，再追加“虎牙 / 斗鱼 / YY / B站”专项回归
5. 如需进一步清仓，再按 `scripts/cleanup_tmp_artifacts.ps1` 实际执行删除
