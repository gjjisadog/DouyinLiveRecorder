# 当前状态

最后更新：2026-04-02

## 已确认
- 当前仓库同时包含两条产品线：
  - 旧版 CLI / 脚本录制主线：`main.py`、`src/`、`msg_push.py`、`ffmpeg_install.py`
  - 新版 PySide6 客户端主线：`client/`
- 客户端基础结构已落地，包含：
  - UI：`client/ui/`
  - ViewModel / 页面协调：`client/viewmodels/`
  - 录制与配置核心：`client/core/`
  - 存储与 Docker / NAS 基础设施：`client/infra/`
- `client/tests/` 已存在完整测试集；此前 handover 记录确认过 76 项测试与 `py_compile` 检查通过。
- 2026-04-01 已完成一轮真实 Docker 构建验收：
  - `docker --version` = `29.3.1`
  - `docker compose version` = `v5.1.0`
  - `docker compose -f docker-compose.flyinnas.yaml up -d --build` 成功
  - 容器 `douyin-live-recorder` 达到 `healthy`
  - 健康检查输出 `recorder healthy with 1 configured target(s)`
  - `client.infra.docker.flyinnas_regression first-deploy` 返回 `PASS`
- 2026-04-01 已把 `BL-004` 推进到“本机回归收口、只差 NAS 宿主机”的状态：
  - `client.tests.test_flyinnas_deploy` 与 `client.tests.test_flyinnas_regression` 共 `11` 项单测通过
  - `client.infra.docker.flyinnas_deploy --dry-run` 可生成 NAS 部署所需的 `scp` / `ssh` 命令
  - `deploy_flyinnas.ps1` 在 `powershell -ExecutionPolicy Bypass -File ...` 方式下可正确走通 PowerShell 入口
  - 本机容器再次启动至 `healthy` 后，`client.infra.docker.flyinnas_regression` 的 `first-deploy` / `upgrade-deploy` / `rollback-deploy` 三个场景均返回 `PASS`
  - 本轮验证结束后已执行 `docker compose down --remove-orphans`，并恢复 `config/URL_config.ini`
- 为解决 Docker 构建过程中 Debian 源偶发 `502 Bad Gateway`，已对 `Dockerfile` 增加显式 `apt` 重试循环。
- 本轮 Docker 验收使用 README 中的公开示例地址临时写入 `config/URL_config.ini`；验收后已恢复原文件内容并执行 `docker compose down --remove-orphans`。
- 2026-04-01 已把 `BL-002` 推进到“工程链路基本闭环”：
  - `winget list --id Gyan.FFmpeg.Essentials` 确认本机装有 `FFmpeg (Essentials Build) 8.1`
  - `client/main.py` 可成功启动，并在真实工作区 `client_data/` 生成 `config.json`、`tasks.json`、`runtime_state.json`、`storage_meta.json`、`client.db`
  - `runtime_state.json` 显示客户端曾进入托盘隐藏状态，说明主窗口链路至少成功运行过一轮
  - 在临时工作区 `tmp_bl002_record_smoke/` 中，已真实跑通“新增任务并保存 → `RecordManager.start_task()` → 录制 8 秒 → `RecordManager.stop_task()` → 历史落档”
  - 已产出录制文件 `tmp_bl002_record_smoke/downloads/BL002_Smoke_Stream/BL002_Smoke_Stream_2026-04-01_23-25-27.ts`
  - `dist/DouyinLiveRecorder Client/DouyinLiveRecorder Client.exe` 已再次真实拉起；进程可存活、可响应，且打包版 `client_data/runtime_state.json` 已刷新
- 2026-04-01 已完成 `BL-005` 平台接入覆盖复核：
  - 客户端当前已接入 `13` 个平台 + 自定义 `m3u8` / `flv` 直链：抖音、TikTok、快手、虎牙、斗鱼、YY、B站、网易 CC、千度热播、PandaTV、百度直播、ShowRoom、CHZZK
  - README 主程序当前列出 `51` 个平台；客户端能力范围不能直接等同于旧版主程序
  - 已确认的自动化证据分层如下：
    - 路由识别：网易 CC、千度热播、PandaTV、百度直播、ShowRoom、CHZZK
    - 解析分支：网易 CC、CHZZK
    - 任务导入 / 展示 / 持久化：抖音、TikTok、快手、ShowRoom、CHZZK
    - `ffmpeg` / 录制相关：抖音、PandaTV、自定义 `m3u8` 直链
  - `README.md` 已新增“客户端当前已迁移平台”说明，避免把旧版主程序的完整平台清单误读为客户端现状
- 2026-04-01 已完成 `BL-006` 配置示例与脱敏说明补齐：
  - 已确认 `config/config.ini` 含有真实风格的 Cookie / 推送 / 账号字段，不能直接作为公开模板
  - 已新增 `config/config.example.ini` 与 `config/URL_config.example.ini`
  - `README.md` 已补充“先复制示例文件再填写真实配置”的使用说明
  - handover 已明确把配置敏感区收敛到 `推送配置`、`Cookie`、`Authorization`、`账号密码`
- 2026-04-01 已完成 `BL-003` 发布说明 / Release Notes 收口：
  - `client/tests/test_build_release.py` 共 `10` 项测试通过
  - `client.build_release --dry-run` 可稳定恢复当前 PyInstaller 构建命令
  - 当前 `dist/` 中仍保留目录版、zip、sha256、manifest.json、manifest.md 五类产物
  - `CLIENT_RELEASE.md` 已明确区分“仓库内可恢复的发布信息”与“缺失 Git 历史后无法恢复的历史 Release Notes”
- 2026-04-02 已完成 `BL-007` 临时目录清理策略：
  - 已盘点根目录 `20` 个 `tmp*` 目录
  - 已确认 `tmp_bl002_record_smoke` 为当前最明确的取证目录，因为它被现有 session 文档直接引用且包含真实录制产物
  - 已将 `tmp*/` 写入 `.gitignore`
  - 已新增 `scripts/cleanup_tmp_artifacts.ps1`，默认 dry-run，且默认保留被 `docs/sessions/` 引用的目录
- 2026-04-02 已将 `BL-008` 推进到“分类完成、待建新基线”的状态：
  - `.git/` 存在，但当前无可读 branch / remote / commit 历史
  - 已确认当前更像“空 Git 仓库 + 完整工作区文件”状态
  - 已把 `client_data/` 与 `tmp_*.log` 补入 `.gitignore`
  - 已形成源码 / 文档 / 模板 / 脚本 与构建 / 运行 / 临时产物的边界分类
  - 仍未实际执行 `git add` / `git commit`

## 推断
- 当前项目目标是：在尽量保留原 `main.py` / `src/` 录制能力的前提下，逐步把常用能力迁移到本地桌面客户端，并同时保留 Docker / NAS 场景。
- Docker / NAS 线目前已具备“仓库内可构建、可健康检查、可跑单测、可跑部署 dry-run、可跑三种回归脚本”的状态，离真正的飞牛云宿主机验证只差 SSH 实机落地。
- 客户端功能面已经覆盖任务、设置、日志、历史、通知等主视图，剩余工作更多偏人工验证、文档收口和边界补档。
- 从“能启动、能持久化、能录、能停、打包可跑”的工程角度看，`BL-002` 已基本收口。
- 客户端平台迁移当前处于“主流程已接线，但自动化验证证据不均匀”的状态；后续补测应优先关注虎牙、斗鱼、YY、B站等已接线但证据偏弱的平台。
- 配置安全边界目前已经比之前清晰：真实配置与可提交样板已分离，但仍需要开发阶段保持“示例文件更新”和“本地敏感值不入库”的纪律。
- 客户端发布流程当前已具备“脚本、测试、产物、校验清单”四件套，但历史变更摘要仍受 Git 基线缺失影响。
- 临时目录治理现在已有最小可用机制，但真正的 Git 基线收口仍取决于后续 `BL-008`。
- Git 侧当前最关键的事实不是“有哪些改动”，而是“还没有任何可追溯提交基线”。

## 待确认
- 真实 NAS / 飞牛云宿主机上的首次部署、升级部署、回滚部署是否都已跑通。
- 客户端是否还需要一轮人工 GUI 手点验收，以补齐“右键菜单 / 行内按钮 / 状态联动”的发布前观察记录。
- 虎牙、斗鱼、YY、B站的客户端解析分支是否已经在当前代码基线下真实可用；目前仓库内只能确认它们“已有接线”，还不能确认“已有客户端专用回归”。
- 历史 Release 页面上的文案、上传记录与 changelog 是否还能从外部来源补回；当前仓库本地不能单独确认。
- 当前仓库与上游 Git 历史的对应关系；现阶段无法从本地确认 commit 基线。
- 是否要在当前仓库直接建立“恢复后的首个提交基线”。

## 当前建议先看
- `README.md`
- `CLIENT_TASK_TRACKER.md`
- `docs/handover/executable_backlog.md`
- `docs/handover/next_steps.md`
- `docs/handover/known_issues.md`
- `docs/sessions/2026-04-01-docker-bl001-validation.md`
- `docs/sessions/2026-04-01-client-bl002-smoke.md`
- `docs/sessions/2026-04-01-flyinnas-bl004-validation.md`
- `docs/sessions/2026-04-01-platform-coverage-bl005.md`
- `docs/sessions/2026-04-01-config-sanitization-bl006.md`
- `docs/sessions/2026-04-01-release-recovery-bl003.md`
- `docs/sessions/2026-04-02-temp-cleanup-bl007.md`
- `docs/sessions/2026-04-02-git-baseline-bl008.md`
