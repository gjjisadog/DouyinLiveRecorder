# 客户端任务台账

最后更新：2026-03-31

## 维护规则

- 客户端相关任务统一记录在本文件，不再分散到临时消息中。
- 每完成一个任务，先更新“任务表”状态，再追加一条“完成记录”。
- 调试、排障、测试验证过程统一追加到“调试记录”，保留问题、原因、处理办法和结果。

## 状态说明

| 状态 | 含义 |
| --- | --- |
| 待办 | 尚未开始 |
| 进行中 | 已开始推进 |
| 阻塞 | 当前有前置问题未解决 |
| 已完成 | 已实现并完成验证 |

## 任务表

| ID | 里程碑 | 优先级 | 模块 | 任务 | 状态 | 验收标准 | 最近更新 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C-001 | M1 可用版 | P0 | 存储/启动链路 | 增强 `config.json`、`tasks.json`、`history.json` 损坏时的容错恢复能力，并补单元测试 | 已完成 | 本地 JSON 损坏时客户端可继续启动；坏文件保留备份；测试通过 | 2026-03-31 |
| C-002 | M1 可用版 | P0 | 平台接入 | 补齐客户端缺失的第一批高频平台迁移，优先覆盖主项目常用平台 | 已完成 | 目标平台可在客户端创建任务、识别平台、解析直播流并开始录制 | 2026-03-31 |
| C-003 | M1 可用版 | P0 | 设置页 | 将巡检间隔、并发数、目录组织、文件命名、代理平台范围、仅通知不录制等核心配置接入 UI | 已完成 | `AppConfig` 核心字段可在设置页编辑并落盘 | 2026-03-31 |
| C-004 | M1 可用版 | P0 | 启动体验 | 增加启动前依赖检查与用户提示，至少覆盖 `ffmpeg` 缺失场景 | 已完成 | 缺依赖时给出可理解提示，不直接异常退出 | 2026-03-31 |
| C-005 | M1 可用版 | P0 | 测试 | 补齐 `scheduler`、`record_worker`、`ffmpeg_service`、`notification_service` 的服务层测试 | 已完成 | 核心服务具备稳定回归测试 | 2026-03-31 |
| C-006 | M2 完整替代版 | P1 | 通知 | 将邮箱、Bark、ntfy、PushPlus 等通知能力接入客户端 | 已完成 | 客户端通知能力接近主项目现有能力面 | 2026-03-31 |
| C-007 | M2 完整替代版 | P1 | 配置迁移 | 补 Cookie、Authorization、Credentials 等高级配置编辑能力 | 已完成 | 用户不需要频繁手改 JSON/INI | 2026-03-31 |
| C-008 | M2 完整替代版 | P1 | 任务管理 | 支持任务批量导入、导出和旧版配置迁移 | 已完成 | 可批量导入旧版 URL 配置并在客户端继续维护 | 2026-03-31 |
| C-009 | M2 完整替代版 | P1 | 架构 | 将页面中的业务逻辑继续下沉到 viewmodel / service，减少 UI 直连逻辑 | 已完成 | 页面层职责更清晰，业务逻辑集中可测 | 2026-03-31 |
| C-010 | M3 正式发布版 | P2 | 存储 | 明确长期存储方案，决定继续使用 JSON 还是迁移到 SQLite | 已完成 | 有清晰存储边界和迁移方案 | 2026-03-31 |
| C-011 | M3 正式发布版 | P2 | 发布 | 增加资源文件、图标、打包配置、版本信息和发布流程 | 已完成 | 客户端可稳定打包分发 | 2026-03-31 |
| C-012 | M3 正式发布版 | P2 | 桌面能力 | 补系统托盘最小化运行、开机启动、崩溃恢复、录制任务恢复 | 已完成 | 具备桌面客户端常用长期运行能力 | 2026-03-31 |

## 附加任务

| ID | 类型 | 优先级 | 模块 | 任务 | 状态 | 验收标准 | 最近更新 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D-001 | 部署 | P0 | Docker | 提供适合飞牛云 / NAS 的无交互 Docker 运行方案 | 已完成 | 容器可无交互启动；配置缺失时明确报错；提供飞牛云部署说明 | 2026-03-31 |

## 当前建议推进顺序

1. Docker 镜像实机构建验收
2. 客户端录制链路二轮人工冒烟
3. 发布说明 / Release Notes 自动生成
4. 飞牛云主机实跑回归记录补档

## 完成记录

### 2026-03-31

#### C-001 存储容错与启动链路加固

- 为 [json_store.py](E:\Project\DouyinLiveRecorder-4.0.7\client\infra\storage\json_store.py) 增加 JSON 读取容错和损坏文件隔离备份能力。
- 在 [config_service.py](E:\Project\DouyinLiveRecorder-4.0.7\client\core\config_service.py)、[task_persistence.py](E:\Project\DouyinLiveRecorder-4.0.7\client\core\task_persistence.py)、[history_service.py](E:\Project\DouyinLiveRecorder-4.0.7\client\core\history_service.py) 接入容错回退逻辑。
- 历史记录加载改为“跳过坏记录、保留好记录”，避免单条脏数据拖垮整个历史页。
- 新增测试文件 [test_storage_resilience.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_storage_resilience.py)。
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
```

- 验证结果：4 个测试全部通过。

#### C-002 第一批平台迁移

- 为 [enums.py](E:\Project\DouyinLiveRecorder-4.0.7\client\core\enums.py)、[platform_router.py](E:\Project\DouyinLiveRecorder-4.0.7\client\core\platform_router.py)、[stream_resolver.py](E:\Project\DouyinLiveRecorder-4.0.7\client\core\stream_resolver.py) 补充第一批客户端已迁移平台。
- 本次接入的平台包括：网易 CC、千度热播、PandaTV、百度直播、ShowRoom、CHZZK。
- 同步更新了 [tasks_page.py](E:\Project\DouyinLiveRecorder-4.0.7\client\ui\pages\tasks_page.py)、[history_page.py](E:\Project\DouyinLiveRecorder-4.0.7\client\ui\pages\history_page.py)、[task_editor_dialog.py](E:\Project\DouyinLiveRecorder-4.0.7\client\ui\dialogs\task_editor_dialog.py) 的平台显示文本。
- 新增测试文件 [test_platform_migration.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_platform_migration.py)，验证平台识别和解析分支接线。
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
```

- 验证结果：7 个测试全部通过。

#### C-003 设置页核心配置补齐

- 扩展了 [settings_page.py](E:\Project\DouyinLiveRecorder-4.0.7\client\ui\pages\settings_page.py) 的设置分组，新增覆盖录制调度、输出目录组织、后处理、代理平台范围等核心配置。
- 本次接入的核心字段包括：并发任务数、巡检间隔、排队等待、仅通知不录制、HTTPS 录制、按主播/日期/标题分目录、文件名包含标题、清理表情字符、磁盘剩余阈值、显示源地址、自动转 MP4、转码 H.264、转码后删除原文件、生成时间字幕文件、自定义脚本、代理平台、额外代理平台。
- 保留原有通知测试能力，同时让新增字段可以从 `AppConfig` 正确加载并回写。
- 新增测试文件 [test_settings_page.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_settings_page.py)，验证设置页对扩展字段的加载和保存。
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
```

- 验证结果：9 个测试全部通过。

#### C-004 启动前依赖检查

- 在 [bootstrap.py](E:\Project\DouyinLiveRecorder-4.0.7\client\bootstrap.py) 接入启动前依赖检查流程，在主窗口创建前检查 `ffmpeg` 是否可用。
- 当检测不到 `ffmpeg` 时，客户端会弹出可理解提示，说明“仍可继续打开客户端，但暂时无法开始录制”，并允许用户选择继续或退出。
- 扩展了 [dependency_checker.py](E:\Project\DouyinLiveRecorder-4.0.7\client\infra\env\dependency_checker.py)，让检查逻辑返回已检测到的 `ffmpeg` 路径，便于日志记录与测试。
- 新增测试文件 [test_bootstrap_dependencies.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_bootstrap_dependencies.py)，覆盖依赖满足、缺失后退出、缺失后继续三种分支。
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
```

- 验证结果：12 个测试全部通过。

#### C-005 核心服务测试补齐

- 新增测试文件 [test_core_services.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_core_services.py)，覆盖了 `Scheduler`、`RecordWorker`、`FfmpegService`、`NotificationService` 的核心分支。
- `Scheduler` 测试覆盖“只启动应启动的任务”和“区分离线/失败任务”。
- `RecordWorker` 测试覆盖“未开播取消启动”“成功启动后写入会话与历史”“录制完成/失败后的状态同步”。
- `FfmpegService` 测试覆盖“代理/HTTPS/header 命令拼装”和“抖音优先选择非 H.265 FLV 源”。
- `NotificationService` 测试覆盖“桌面与远端渠道同时分发”“缺失配置时的结果反馈”“远端成功/部分成功/失败消息”。
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
```

- 验证结果：22 个测试全部通过。

#### C-006 通知能力补齐

- 在 [notification_service.py](E:\Project\DouyinLiveRecorder-4.0.7\client\core\notification_service.py) 新增了 `Bark`、`ntfy`、`PushPlus`、`邮件` 四类远端通知渠道，并补充了对应的渠道别名、配置读取与结果汇总逻辑。
- 在 [settings_page.py](E:\Project\DouyinLiveRecorder-4.0.7\client\ui\pages\settings_page.py) 的通知设置区域补充了新渠道所需字段和测试发送按钮。
- 邮件通知本次接入了 SMTP 服务器、账号、密码、发件邮箱、发件人名称、收件邮箱、端口和 SSL 开关等核心配置。
- 同步扩展了 [test_core_services.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_core_services.py) 与 [test_settings_page.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_settings_page.py)，验证新增渠道分发和设置页字段映射。
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
```

- 验证结果：22 个测试全部通过。

#### C-007 高级配置编辑

- 在 [settings_page.py](E:\Project\DouyinLiveRecorder-4.0.7\client\ui\pages\settings_page.py) 新增“高级配置”区域，用键值编辑器方式接入 `Cookie`、`Authorization`、`账号密码` 三类原始配置。
- 采用“每行一项、键 = 值”的编辑方式，兼容大量平台 Cookie 与授权参数，避免把几十项字段拆成零散输入框。
- 保存时会把高级配置文本解析回 `AppConfig.cookies`、`AppConfig.authorization`、`AppConfig.credentials`，并与独立的抖音 Cookie 字段保持同步。
- 扩展了 [test_settings_page.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_settings_page.py)，验证高级配置在设置页中的加载、解析与回写行为。
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
```

- 验证结果：22 个测试全部通过。

#### D-001 飞牛云 Docker 适配

- 新增 [DOCKER_FLYINNAS.md](E:\Project\DouyinLiveRecorder-4.0.7\DOCKER_FLYINNAS.md)，整理飞牛云 / NAS 场景下的目录挂载、启动命令和常见问题说明。
- 新增 [docker-compose.flyinnas.yaml](E:\Project\DouyinLiveRecorder-4.0.7\docker-compose.flyinnas.yaml)，提供更适合 NAS 的 Compose 示例。
- 优化了 [Dockerfile](E:\Project\DouyinLiveRecorder-4.0.7\Dockerfile) 与 [docker-compose.yaml](E:\Project\DouyinLiveRecorder-4.0.7\docker-compose.yaml)，默认启用无交互模式，并使用 [requirements.docker.txt](E:\Project\DouyinLiveRecorder-4.0.7\requirements.docker.txt) 避免在容器中安装桌面客户端依赖。
- 在 [main.py](E:\Project\DouyinLiveRecorder-4.0.7\main.py) 增加了 `DLR_HEADLESS` 支持：当 `URL_config.ini` 为空且处于无交互环境时，程序会直接输出错误并退出，避免容器卡在 `input()`。
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
& '.\.client-conda-env\python.exe' -m py_compile main.py
```

- 验证结果：22 个测试全部通过，`main.py` 编译检查通过。

#### D-001 Docker 镜像与飞牛云部署收口增强

- 扩展 [.dockerignore](E:\Project\DouyinLiveRecorder-4.0.7\.dockerignore)，排除 `.client-conda-env`、`dist`、`build`、日志目录和临时目录，避免镜像构建把本地开发产物一并打包进去。
- 新增 [healthcheck.py](E:\Project\DouyinLiveRecorder-4.0.7\client\infra\docker\healthcheck.py) 与 [test_docker_healthcheck.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_docker_healthcheck.py)，把 Docker 健康检查固化为“`URL_config.ini` 非空 + `python main.py` 主进程仍在运行”。
- 更新 [Dockerfile](E:\Project\DouyinLiveRecorder-4.0.7\Dockerfile)，加入 `HEALTHCHECK` 指令；同步重写 [docker-compose.yaml](E:\Project\DouyinLiveRecorder-4.0.7\docker-compose.yaml) 与 [docker-compose.flyinnas.yaml](E:\Project\DouyinLiveRecorder-4.0.7\docker-compose.flyinnas.yaml)，默认构建当前仓库版本，固定镜像标签为 `douyin-live-recorder:4.0.7`，并开启健康检查。
- 新增 [DOCKER_FLYINNAS_CHECKLIST.md](E:\Project\DouyinLiveRecorder-4.0.7\DOCKER_FLYINNAS_CHECKLIST.md)，同时更新 [DOCKER_FLYINNAS.md](E:\Project\DouyinLiveRecorder-4.0.7\DOCKER_FLYINNAS.md)，补齐飞牛云一键部署前置条件、启动命令、健康检查和回滚动作清单。
- 新增 [release.py](E:\Project\DouyinLiveRecorder-4.0.7\client\infra\docker\release.py)、[test_docker_release.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_docker_release.py)、[build_docker_release.ps1](E:\Project\DouyinLiveRecorder-4.0.7\build_docker_release.ps1)、[build_docker_release.bat](E:\Project\DouyinLiveRecorder-4.0.7\build_docker_release.bat)，补齐 buildx 多架构发布脚本，并统一镜像版本标签来源到 [version.py](E:\Project\DouyinLiveRecorder-4.0.7\client\version.py)。
- 新增 [.env.docker.example](E:\Project\DouyinLiveRecorder-4.0.7\.env.docker.example)，把 Compose 默认镜像仓库名/标签提取为 `DLR_IMAGE_REPOSITORY` 与 `DLR_IMAGE_TAG`；同时更新 [build-image.yml](E:\Project\DouyinLiveRecorder-4.0.7\.github\workflows\build-image.yml)，让 GitHub Actions 通过统一的 Docker 发布模块生成 tags/platforms。
- 新增 [DOCKER_FLYINNAS_REGRESSION.md](E:\Project\DouyinLiveRecorder-4.0.7\DOCKER_FLYINNAS_REGRESSION.md)，把飞牛云回归清单按“首次部署 / 升级部署 / 回滚部署”三条路径拆开；同步更新 [README.md](E:\Project\DouyinLiveRecorder-4.0.7\README.md) 的 Docker 使用说明，移除旧的 `latest` / 手改 Compose 指引。
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m unittest client.tests.test_docker_healthcheck -v
& '.\.client-conda-env\python.exe' -m unittest client.tests.test_docker_release -v
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
& '.\.client-conda-env\python.exe' -m py_compile client\infra\docker\release.py client\infra\docker\healthcheck.py client\tests\test_docker_release.py client\tests\test_docker_healthcheck.py main.py
& '.\.client-conda-env\python.exe' -m client.infra.docker.release print-version
& '.\.client-conda-env\python.exe' -m client.infra.docker.release print-compose-env
& '.\.client-conda-env\python.exe' -m client.infra.docker.release print-tags --repository ihmily/douyin-live-recorder
& '.\.client-conda-env\python.exe' -m client.infra.docker.release buildx --repository ihmily/douyin-live-recorder --repo-root '.' --push --dry-run
```

- 验证结果：新增 5 个 Docker 健康检查测试与 8 个 Docker 发布脚本测试全部通过；当前客户端测试共 56 项全部通过；发布模块可正确输出版本号、Compose 环境变量、镜像 tags 与 buildx dry-run 命令。当前环境无 `docker` 命令，尚未完成镜像实构建与 `docker compose` 实跑验收。

#### C-008 任务批量导入导出与旧版配置迁移

- 在 [task_persistence.py](E:\Project\DouyinLiveRecorder-4.0.7\client\core\task_persistence.py) 增加任务文件导入、导出和合并能力，支持本地 JSON、旧版 `URL_config.ini` / `txt` 文本格式，以及按归一化 URL 去重合并。
- 新增“导入任务 / 导出任务”入口到 [tasks_page.py](E:\Project\DouyinLiveRecorder-4.0.7\client\ui\pages\tasks_page.py)，导入后会同步刷新 `viewmodel`、补齐 `record_manager` 中的新任务，并落盘到本地 `tasks.json`。
- 导入合并策略为：同 URL 任务优先复用旧任务 ID，更新画质、显示名、启用状态；正在运行的任务不覆盖，计入跳过；导出时可回写旧版文本格式，便于回退或兼容主项目历史配置。
- 新增测试文件 [test_task_import_export.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_task_import_export.py)，覆盖旧版文本解析、JSON 导入、URL 去重合并、JSON/旧版文本导出，以及任务页导入后持久化链路。
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m unittest client.tests.test_task_import_export -v
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
& '.\.client-conda-env\python.exe' -m py_compile client\core\task_persistence.py client\ui\pages\tasks_page.py
```

- 验证结果：新增 7 个 C-008 测试全部通过；当前客户端测试共 29 项全部通过；相关文件编译检查通过。

#### C-009 任务页业务逻辑下沉

- 在 [task_viewmodel.py](E:\Project\DouyinLiveRecorder-4.0.7\client\viewmodels\task_viewmodel.py) 增加 `TaskActionResult`，把任务创建、编辑、导入、导出、删除、启停、默认画质、运行态判断、任务筛选和摘要统计统一沉到 `TaskViewModel`。
- 重构 [tasks_page.py](E:\Project\DouyinLiveRecorder-4.0.7\client\ui\pages\tasks_page.py)，页面层改为只负责文件选择、编辑对话框、删除确认、表格渲染和结果提示；核心业务动作全部通过 `viewmodel` 执行。
- 新增测试文件 [test_task_viewmodel.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_task_viewmodel.py)，覆盖任务创建落盘、导入合并、删除持久化、启动失败错误回写，以及中文平台/状态筛选与摘要文案。
- 保留并复用已有的 [test_task_import_export.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_task_import_export.py)，确保任务页导入导出 UI 链路在重构后仍然可用。
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m unittest client.tests.test_task_viewmodel -v
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
& '.\.client-conda-env\python.exe' -m py_compile client\viewmodels\task_viewmodel.py client\ui\pages\tasks_page.py
```

- 验证结果：新增 5 个 C-009 测试全部通过；当前客户端测试共 34 项全部通过；重构文件编译检查通过。

#### C-010 存储方案收口

- 新增 [CLIENT_STORAGE_STRATEGY.md](E:\Project\DouyinLiveRecorder-4.0.7\CLIENT_STORAGE_STRATEGY.md)，明确客户端当前采用“JSON 主存储 + SQLite 迁移基座”的长期方案，并写清配置、任务、历史、迁移基座的边界与后续迁移顺序。
- 在 [storage_strategy.py](E:\Project\DouyinLiveRecorder-4.0.7\client\infra\storage\storage_strategy.py) 实现存储策略清单服务，启动时会写出 `client_data/storage_meta.json`，记录模式、边界、迁移阶段和 SQLite 准备状态。
- 将 [sqlite_repo.py](E:\Project\DouyinLiveRecorder-4.0.7\client\infra\storage\sqlite_repo.py) 从占位符升级为可用的 SQLite 基础仓储，支持初始化 `app_metadata` / `migrations` 表并读取 schema 版本与元信息。
- 在 [bootstrap.py](E:\Project\DouyinLiveRecorder-4.0.7\client\bootstrap.py) 接入存储策略初始化；在 [app_settings.py](E:\Project\DouyinLiveRecorder-4.0.7\client\app_settings.py) 增加 `storage_meta.json` 路径配置。
- 新增测试文件 [test_storage_strategy.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_storage_strategy.py)，覆盖存储策略清单写出、SQLite schema 元信息初始化和启动初始化链路。
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m unittest client.tests.test_storage_strategy -v
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
& '.\.client-conda-env\python.exe' -m py_compile client\infra\storage\storage_strategy.py client\infra\storage\sqlite_repo.py client\bootstrap.py
```

- 验证结果：新增 3 个 C-010 测试全部通过；当前客户端测试共 37 项全部通过；相关文件编译检查通过。

#### C-011 发布与打包链路落地

- 新增 [version.py](E:\Project\DouyinLiveRecorder-4.0.7\client\version.py) 作为客户端统一版本元数据入口，并在 [app_settings.py](E:\Project\DouyinLiveRecorder-4.0.7\client\app_settings.py)、[main_window.py](E:\Project\DouyinLiveRecorder-4.0.7\client\ui\main_window.py) 中接入产品名、版本号和运行时图标信息。
- 新增 [build_release.py](E:\Project\DouyinLiveRecorder-4.0.7\client\build_release.py)、[build_client_release.ps1](E:\Project\DouyinLiveRecorder-4.0.7\build_client_release.ps1)、[build_client_release.bat](E:\Project\DouyinLiveRecorder-4.0.7\build_client_release.bat)、[requirements.client-build.txt](E:\Project\DouyinLiveRecorder-4.0.7\requirements.client-build.txt)，补齐 Windows 客户端的 PyInstaller 打包入口、版本信息文件生成、资源目录打包和图标嵌入流程。
- 补充 [app_icon.svg](E:\Project\DouyinLiveRecorder-4.0.7\client\resources\app_icon.svg)、[app_icon.ico](E:\Project\DouyinLiveRecorder-4.0.7\client\resources\app_icon.ico) 与 [CLIENT_RELEASE.md](E:\Project\DouyinLiveRecorder-4.0.7\CLIENT_RELEASE.md)，把发布依赖、构建命令、产物目录和人工检查项写成仓库内文档。
- 新增测试文件 [test_build_release.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_build_release.py)，覆盖默认路径、Windows 版本信息、PyInstaller 参数与图标装配逻辑。
- 为 [build_release.py](E:\Project\DouyinLiveRecorder-4.0.7\client\build_release.py) 增加 conda `Library/bin` 运行时 DLL 收包逻辑，补齐 PySide6 / Shiboken / Qt 核心动态库，解决打包产物启动即崩问题。
- 实际打包与 GUI 启动冒烟已通过，当前产物位于 `dist/DouyinLiveRecorder Client/`，其中 `DouyinLiveRecorder Client.exe` 已重新生成并可正常拉起主窗口。
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m unittest client.tests.test_build_release -v
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
& '.\.client-conda-env\python.exe' -m client.build_release --python '.\.client-conda-env\python.exe' --repo-root '.' --dry-run
& '.\.client-conda-env\python.exe' -m client.build_release --python '.\.client-conda-env\python.exe' --repo-root '.'
```

- GUI 冒烟验证：

```powershell
$exeDir = 'E:\Project\DouyinLiveRecorder-4.0.7\dist\DouyinLiveRecorder Client'
$stubDir = Join-Path $exeDir 'smoke-bin'
Set-Content -LiteralPath (Join-Path $stubDir 'ffmpeg.bat') -Encoding ASCII -Value "@echo off`r`necho ffmpeg smoke stub`r`n"
$env:PATH = "$stubDir;$env:PATH"
Start-Process -FilePath (Join-Path $exeDir 'DouyinLiveRecorder Client.exe') -WorkingDirectory $exeDir -PassThru
```

- 验证结果：`C-011` 专项测试 6 项通过；当前客户端测试共 43 项全部通过；PyInstaller 真实构建成功；GUI 冷启动时主窗口标题为 `DouyinLiveRecorder Client 4.0.7`，窗口句柄与响应状态正常；首次启动已写出 `client.db`、`config.json`、`storage_meta.json`、`tasks.json`。当前宿主机未安装 `ffmpeg`，本轮使用临时 stub 绕过依赖提示完成窗口级冒烟；`history.json` 仍按首次写入历史时再创建。

#### C-012 桌面常驻能力收口

- 在 [desktop_runtime.py](E:\Project\DouyinLiveRecorder-4.0.7\client\infra\process\desktop_runtime.py) 新增桌面运行时服务，统一管理 `runtime_state.json`、Windows 开机启动注册表写入与异常退出恢复快照。
- 在 [app_settings.py](E:\Project\DouyinLiveRecorder-4.0.7\client\app_settings.py)、[models.py](E:\Project\DouyinLiveRecorder-4.0.7\client\core\models.py)、[config_service.py](E:\Project\DouyinLiveRecorder-4.0.7\client\core\config_service.py) 补齐桌面常驻相关配置字段与本地序列化，包括最小化到托盘、关闭转托盘、开机启动、异常任务恢复、启动时恢复桌面状态。
- 在 [settings_page.py](E:\Project\DouyinLiveRecorder-4.0.7\client\ui\pages\settings_page.py)、[main_window.py](E:\Project\DouyinLiveRecorder-4.0.7\client\ui\main_window.py)、[bootstrap.py](E:\Project\DouyinLiveRecorder-4.0.7\client\bootstrap.py) 接通托盘菜单、最小化/关闭转后台、启动快照恢复、异常任务恢复、退出时干净落盘以及启动链路中的运行时服务注入。
- 新增 [test_desktop_runtime.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_desktop_runtime.py)、[test_main_window_runtime.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_main_window_runtime.py)，并扩展 [test_settings_page.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_settings_page.py) 覆盖桌面配置加载/保存与开机启动状态回写。
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m py_compile client\ui\main_window.py client\bootstrap.py client\ui\pages\settings_page.py client\tests\test_desktop_runtime.py client\tests\test_main_window_runtime.py
& '.\.client-conda-env\python.exe' -m unittest client.tests.test_desktop_runtime client.tests.test_main_window_runtime client.tests.test_settings_page -v
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
```

- 验证结果：`C-012` 专项回归 7 项全部通过；当前客户端测试总数提升到 61 项并全部通过。托盘关闭转后台、启动时恢复上次桌面状态、异常任务恢复与开机启动状态同步链路已打通。

#### C-011 发布产物压缩、校验和与清单收口

- 扩展 [build_release.py](E:\Project\DouyinLiveRecorder-4.0.7\client\build_release.py)，在 PyInstaller 目录版构建完成后自动生成版本化 zip、SHA256 校验清单、JSON 发布清单和 Markdown 发布清单，并补充 `--skip-package` 开关。
- 扩展 [test_build_release.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_build_release.py)，覆盖归档命名、zip 根目录结构、manifest 文件内容以及完整产物输出链路。
- 更新 [CLIENT_RELEASE.md](E:\Project\DouyinLiveRecorder-4.0.7\CLIENT_RELEASE.md)，写明新增产物文件、PowerShell 校验命令、构建参数与发版检查步骤。
- 已在当前工作区实际生成以下发布文件：
  - `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.zip`
  - `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.sha256`
  - `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.manifest.json`
  - `dist/DouyinLiveRecorder-Client-4.0.7-windows-x64.manifest.md`
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m py_compile client\build_release.py client\tests\test_build_release.py
& '.\.client-conda-env\python.exe' -m unittest client.tests.test_build_release -v
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
& '.\.client-conda-env\python.exe' -m client.build_release --python '.\.client-conda-env\python.exe' --repo-root '.'
```

- 验证结果：`C-011` 构建专项测试提升到 10 项并全部通过；当前客户端测试总数提升到 65 项并全部通过；实际发包后已产出目录版、zip、sha256、manifest.json、manifest.md 五类发布交付物。

#### D-001 飞牛云运行体验回归脚本收口

- 新增 [flyinnas_regression.py](E:\Project\DouyinLiveRecorder-4.0.7\client\infra\docker\flyinnas_regression.py)，把飞牛云 / NAS 的首次部署、升级部署、回滚部署回归整理成可执行脚本，覆盖挂载目录、URL 配置、Docker / Compose 可用性、Compose 解析、容器运行状态、健康检查、镜像标签和最近日志异常模式。
- 新增 [test_flyinnas_regression.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_flyinnas_regression.py)，覆盖首次部署通过、URL 配置为空失败、升级标签不匹配失败、日志异常失败等关键分支。
- 更新 [DOCKER_FLYINNAS.md](E:\Project\DouyinLiveRecorder-4.0.7\DOCKER_FLYINNAS.md)、[DOCKER_FLYINNAS_CHECKLIST.md](E:\Project\DouyinLiveRecorder-4.0.7\DOCKER_FLYINNAS_CHECKLIST.md)、[DOCKER_FLYINNAS_REGRESSION.md](E:\Project\DouyinLiveRecorder-4.0.7\DOCKER_FLYINNAS_REGRESSION.md)，把飞牛云回归从纯手工清单补齐为“清单 + 命令”双轨说明。
- 飞牛云主机上的推荐执行方式：
  - `python -m client.infra.docker.flyinnas_regression first-deploy --app-root .`
  - `python -m client.infra.docker.flyinnas_regression upgrade-deploy --app-root . --expected-tag 4.0.7`
  - `python -m client.infra.docker.flyinnas_regression rollback-deploy --app-root . --expected-tag <目标旧版本>`
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m py_compile client\infra\docker\flyinnas_regression.py client\tests\test_flyinnas_regression.py
& '.\.client-conda-env\python.exe' -m unittest client.tests.test_flyinnas_regression -v
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
```

- 验证结果：飞牛云回归专项测试 5 项全部通过；当前客户端测试总数提升到 70 项并全部通过。当前开发环境仍未安装 Docker，尚未完成飞牛云主机上的真实容器实跑，但仓库内已具备可直接上 NAS 执行的自动化回归入口。

#### D-001 飞牛云 SSH 一键部署脚本

- 新增 [flyinnas_deploy.py](E:\Project\DouyinLiveRecorder-4.0.7\client\infra\docker\flyinnas_deploy.py)，实现本机到飞牛 NAS 的 SSH 部署链路：本地打包代码、通过 `scp` 上传、远端解包、保留已有配置、执行 `docker compose up -d --build`、再触发飞牛回归脚本。
- 新增 [deploy_flyinnas.ps1](E:\Project\DouyinLiveRecorder-4.0.7\deploy_flyinnas.ps1) 与 [deploy_flyinnas.sh](E:\Project\DouyinLiveRecorder-4.0.7\deploy_flyinnas.sh)，分别作为 Windows 和 Unix 侧的一键入口。
- 新增 [test_flyinnas_deploy.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_flyinnas_deploy.py)，覆盖部署包内容、`scp` / `ssh` 命令拼装、远端脚本关键行为和 `dry-run` 输出。
- 更新 [DOCKER_FLYINNAS.md](E:\Project\DouyinLiveRecorder-4.0.7\DOCKER_FLYINNAS.md)，补充 SSH 一键部署的 PowerShell / Bash 用法、参数说明和行为边界。
- 验证命令：

```powershell
& '.\.client-conda-env\python.exe' -m py_compile client\infra\docker\flyinnas_deploy.py client\tests\test_flyinnas_deploy.py
& '.\.client-conda-env\python.exe' -m unittest client.tests.test_flyinnas_deploy -v
& '.\.client-conda-env\python.exe' -m unittest discover -s client\tests -v
powershell -ExecutionPolicy Bypass -File '.\deploy_flyinnas.ps1' -RemoteHost '192.168.1.20' -User 'admin' -Scenario 'first-deploy' -DryRun
```

- 验证结果：SSH 部署专项测试 6 项全部通过；当前客户端测试总数提升到 76 项并全部通过；PowerShell 一键部署入口已能正确输出 `scp` / `ssh` 干跑命令。

## 调试记录

### 2026-03-31

#### 调试条目 001：系统 `python` 不可用

- 现象：直接运行 `python --version` 和 `python -m unittest ...` 失败。
- 原因：当前环境中的 `python` 指向 `C:\Users\wxw\AppData\Local\Microsoft\WindowsApps\python.exe`，无法实际执行。
- 处理：改为使用工程内解释器 `.\.client-conda-env\python.exe` 运行测试。
- 结果：测试命令可正常执行。

#### 调试条目 002：系统临时目录权限异常

- 现象：测试中使用 `TemporaryDirectory()` 时，在系统临时目录下创建 `client_data` 子目录报 `PermissionError: [WinError 5] 拒绝访问`。
- 原因：当前运行环境对系统临时目录写入存在限制或异常。
- 处理：将测试工作目录切换到工程根目录下按 UUID 创建的临时目录，并在测试结束后自动清理。
- 结果：测试环境稳定，后续单元测试全部通过。

#### 调试条目 003：新增日志分支缺少常量导入

- 现象：`TaskPersistenceService` 新增容错日志后，测试报 `NameError: LEVEL_WARNING is not defined`。
- 原因：添加 `_handle_store_error()` 时遗漏了 `LEVEL_WARNING` 的 import。
- 处理：补充 `task_persistence.py` 的日志常量导入。
- 结果：测试恢复正常。

#### 调试条目 004：依赖检查回调类型注解错误

- 现象：新增启动依赖检查测试后，`test_bootstrap_dependencies` 导入失败，报 `TypeError: unsupported operand type(s) for |: 'builtin_function_or_method' and 'NoneType'`。
- 原因：在 [bootstrap.py](E:\Project\DouyinLiveRecorder-4.0.7\client\bootstrap.py) 中把提示回调的类型误写成了内建 `callable`，并与 `| None` 组合使用。
- 处理：改为使用 `collections.abc.Callable[[str, str], bool]`。
- 结果：依赖检查测试恢复正常，全量测试通过。

#### 调试条目 005：调度器测试时间轴不一致

- 现象：新增 `Scheduler` 测试后，`tick()` 没有执行巡检逻辑，导致“未启动任务”“未写入离线错误”两个断言失败。
- 原因：测试里使用了固定的 `now` 时间，但 `scheduler.start()` 内部使用真实 `datetime.now()` 生成 `_next_run_at`，两者不在同一时间轴上。
- 处理：在测试中显式设置 `scheduler._next_run_at` 为同一个固定时间点，再调用 `tick(now=...)`。
- 结果：调度器测试稳定通过。

#### 调试条目 006：中文 UI 文件局部补丁匹配失败

- 现象：在 [task_persistence.py](E:\Project\DouyinLiveRecorder-4.0.7\client\core\task_persistence.py) 与 [tasks_page.py](E:\Project\DouyinLiveRecorder-4.0.7\client\ui\pages\tasks_page.py) 上做局部 `apply_patch` 时，多次出现上下文匹配失败。
- 原因：文件内已有较多中文文案，终端回显存在编码噪音，导致局部补丁的上下文片段不稳定。
- 处理：改为整文件重写，并立即补充 `py_compile` 与回归测试，确保重写没有引入行为回退。
- 结果：文件成功更新，`C-008` 相关测试和全量测试均通过。

#### 调试条目 007：筛选逻辑下沉后中文搜索能力回退风险

- 现象：将任务筛选逻辑从 [tasks_page.py](E:\Project\DouyinLiveRecorder-4.0.7\client\ui\pages\tasks_page.py) 下沉到 [task_viewmodel.py](E:\Project\DouyinLiveRecorder-4.0.7\client\viewmodels\task_viewmodel.py) 后，如果只按枚举值过滤，会丢失“抖音”“运行中”等中文关键词搜索能力。
- 原因：枚举原始值主要用于内部状态与平台标识，和任务页原有的中文展示标签并不完全一致。
- 处理：在 `TaskViewModel` 中补充平台与状态的中文搜索词映射，并新增对应回归测试。
- 结果：重构后中文平台名、中文状态和原有 URL / 主播 / 标题筛选都可继续工作。

#### 调试条目 008：C-010 是否应直接切换 SQLite

- 现象：进入 `C-010` 后，仓库内已存在 [sqlite_repo.py](E:\Project\DouyinLiveRecorder-4.0.7\client\infra\storage\sqlite_repo.py) 占位文件，存在“趁机把 config/tasks/history 一次性迁到 SQLite”的诱因。
- 原因：SQLite 在结构化查询与后续扩展上更强，但当前客户端的配置、任务、历史三条链路都已围绕 JSON 建立兼容、容错和回退测试，直接切库会显著扩大回归面。
- 处理：本轮明确决策为“继续使用 JSON 作为当前主存储，同时把 SQLite 迁移基座真正实现并接入启动流程”，先把边界、元信息和迁移路径固化下来。
- 结果：`storage_meta.json` 与 `client.db` 会在启动时自动初始化，项目后续如需把历史索引或统计迁到 SQLite，已经有明确入口和版本基础。

#### 调试条目 009：客户端环境初始缺少 PyInstaller

- 现象：首次执行 `python -m client.build_release ...` 时失败，提示找不到 `PyInstaller` 模块。
- 原因：客户端原有运行环境只覆盖开发与测试依赖，尚未补充发布打包依赖。
- 处理：新增 [requirements.client-build.txt](E:\Project\DouyinLiveRecorder-4.0.7\requirements.client-build.txt)，并通过 `& '.\.client-conda-env\python.exe' -m pip install -r requirements.client-build.txt` 为工程内解释器安装打包依赖。
- 结果：打包脚本可正常调用 `PyInstaller`，后续 dry-run 与真实构建均可执行。

#### 调试条目 010：Conda 环境下 PyInstaller 存在 Qt 依赖告警噪音

- 现象：真实构建成功后，控制台与 [warn-DouyinLiveRecorder Client.txt](E:\Project\DouyinLiveRecorder-4.0.7\build\client-release\work\DouyinLiveRecorder Client\warn-DouyinLiveRecorder Client.txt) 中仍输出大量 `Qt6Core.dll`、`Qt6Gui.dll`、`libssl-3-x64.dll` 等未解析告警。
- 原因：当前客户端使用 conda 环境，PyInstaller 在扫描 `Library\\lib\\qt6\\plugins` 下的可选 Qt 插件时，会把部分未实际启用或由运行目录补齐的依赖也列入告警清单，导致 warning 数量偏多。
- 处理：先确认 `Build complete!` 已成功产出 `dist/DouyinLiveRecorder Client/`，并把 warning 文件路径记录到发布文档与任务台账，暂按“需关注但不阻塞构建”的已知现象处理。
- 结果：当前可稳定重复打包；后续若 GUI 冒烟发现缺失插件或 DLL，再据具体模块定向裁剪或补齐收包规则。

#### 调试条目 011：首次 GUI 冒烟时打包产物在 `import PySide6` 阶段崩溃

- 现象：从 [DouyinLiveRecorder Client.exe](E:\Project\DouyinLiveRecorder-4.0.7\dist\DouyinLiveRecorder Client\DouyinLiveRecorder Client.exe) 冷启动后，没有进入主窗口，而是出现标题为 `Unhandled exception in script` 的异常窗口。
- 原因：临时控制台调试包显示 `ImportError: DLL load failed while importing Shiboken`；正式 `dist` 产物缺少 `shiboken6.cp311-win_amd64.dll`、`pyside6.cp311-win_amd64.dll` 与 `Qt6Core.dll` 等 conda 运行时 DLL。
- 处理：在 [build_release.py](E:\Project\DouyinLiveRecorder-4.0.7\client\build_release.py) 中新增 conda `Library/bin` DLL 收集逻辑，并补充 [test_build_release.py](E:\Project\DouyinLiveRecorder-4.0.7\client\tests\test_build_release.py) 回归测试后重新打包。
- 结果：重打后的 `dist` 产物已包含核心 PySide6 / Shiboken / Qt DLL，GUI 启动恢复正常。

#### 调试条目 012：宿主机缺少 `ffmpeg`，GUI 冒烟需绕过依赖提示

- 现象：本机 `Get-Command ffmpeg` 返回空值，按默认流程启动客户端会先进入“缺少录制依赖”确认提示，而不是直接展示主窗口。
- 原因：客户端启动阶段新增了 `ffmpeg` 前置检查，而当前宿主机没有把 `ffmpeg` 放进 `PATH`。
- 处理：在产物目录临时创建 `smoke-bin\\ffmpeg.bat` 桩文件并前置到 `PATH`，仅用于本轮窗口级启动冒烟，不写入正式构建流程。
- 结果：可以在不改动业务代码的前提下验证正式 `dist` 产物是否能正常进入主窗口；后续若要做完整录制链路冒烟，仍需安装真实 `ffmpeg`。

#### 调试条目 013：当前环境缺少 Docker，无法完成镜像实构建验收

- 现象：执行 `docker --version` 与 `docker compose version` 时，PowerShell 直接报 `docker` 命令不存在。
- 原因：当前开发环境未安装 Docker Desktop / Docker Engine，也没有可用的 Compose CLI。
- 处理：本轮改为通过 [healthcheck.py](E:\Project\DouyinLiveRecorder-4.0.7\client\infra\docker\healthcheck.py) 单元测试、全量客户端测试、`py_compile` 和静态文件复核来收口 Docker 改动，并在文档中明确“尚缺镜像实构建验收”。
- 结果：Docker 配置与健康检查逻辑已补齐，但仍需在装有 Docker 的飞牛云或 Linux 主机上执行 `docker compose -f docker-compose.flyinnas.yaml up -d --build` 做最后实跑确认。

#### 调试条目 014：buildx 在 `--load` 模式下不能直接输出多架构镜像

- 现象：首次为发布模块做 dry-run 时，默认命令形如 `docker buildx build --platform linux/amd64,linux/arm64 --load ...`，这在本地加载模式下并不是有效组合。
- 原因：`buildx` 的多架构构建需要配合 `--push` 发布到 registry；`--load` 只能把单架构镜像导回本地 Docker。
- 处理：调整 [release.py](E:\Project\DouyinLiveRecorder-4.0.7\client\infra\docker\release.py) 为“`--push` 保持多架构，`--load` 自动退回到首个平台 `linux/amd64`”，并补充对应回归测试。
- 结果：现在 `--dry-run` / 本地加载场景输出的是有效单架构命令，而真实多架构发布仍通过 `--push` 走 `linux/amd64,linux/arm64`。

#### 调试条目 015：托盘行为被通知服务初始化短路

- 现象：主窗口已经加入了“关闭转托盘 / 最小化到托盘”逻辑，但在未注入 `NotificationService` 的场景下，托盘图标根本不会创建，导致整条桌面常驻链路失效。
- 原因：`MainWindow._setup_notifications()` 早期实现把“托盘创建”和“通知发送器绑定”耦合在一起，一旦 `notification_service is None` 就直接 `return`。
- 处理：把托盘图标与菜单创建改为独立于通知服务执行，仅在通知服务存在时再绑定 `set_sender()`；同时补充主窗口运行时回归测试覆盖关闭转托盘与启动恢复隐藏窗口场景。
- 结果：托盘常驻能力不再依赖远程通知模块，`C-012` 的核心交互链路可单独工作。

#### 调试条目 016：启动状态恢复条件与开机启动持久化顺序不一致

- 现象：一方面，“启动时恢复上次桌面状态”勾选后并不会按上次隐藏到托盘的状态恢复；另一方面，设置页里 `start_on_boot` 可能已经被运行时服务纠正，但本地配置文件仍保存旧值。
- 原因：`MainWindow._should_start_hidden_on_launch()` 把 `restore_window_on_launch` 的条件写反了；`SettingsPage._save_settings()` 先 `config_service.save()`，后 `apply_startup_setting()`，导致配置落盘与系统实际状态可能漂移。
- 处理：修正主窗口的恢复条件与启动阶段执行顺序，并把设置页调整为“先应用开机启动，再保存最终配置”，同时为关闭流程加入幂等保护，避免 `aboutToQuit` 与 `closeEvent` 双写退出状态。
- 结果：启动隐藏恢复逻辑与复选框语义一致，`config.json` 中的开机启动状态也会和系统实际结果保持同步。

#### 调试条目 017：发布清单与校验和存在“自引用”设计风险

- 现象：在给发布流程补 `manifest` 与 `sha256` 时，如果让校验清单参与自身摘要计算，或者让 manifest 先写入包含自身最终哈希的数据，会形成循环依赖，导致每次生成结果都不稳定。
- 原因：校验文件与发布清单都属于“描述发布产物的元文件”，一旦把自己的最终内容也纳入被描述对象，就会出现先后顺序无法收敛的问题。
- 处理：将发布流程改为“两阶段写入”：先生成 zip 和基础 manifest，再计算 zip / exe / manifest 的哈希并写出 `.sha256`，最后把 `.sha256` 作为单独产物回填进 manifest 的 artifact 列表，但不再反向重写校验清单。
- 结果：当前生成的 zip、manifest.json、manifest.md、sha256 都是稳定可复现的，既能让 `sha256` 清单直接校验交付物，也能让 manifest 正确列出完整产物集。

#### 调试条目 018：当前环境缺少 Docker，飞牛云回归无法在本机实跑

- 现象：本轮尝试继续推进飞牛云运行回归时，`docker --version` 仍然直接报 PowerShell 找不到 `docker` 命令，说明当前开发环境依旧没有 Docker / Compose。
- 原因：当前机器并非飞牛云宿主机，也未安装 Docker Desktop 或等效 Docker Engine，无法对 `docker-compose.flyinnas.yaml` 做真实容器启动、升级和回滚验证。
- 处理：将飞牛云回归收口为“可执行回归脚本 + 文档命令化 + 单元测试覆盖”，新增 [flyinnas_regression.py](E:\Project\DouyinLiveRecorder-4.0.7\client\infra\docker\flyinnas_regression.py) 并配套更新三份飞牛云文档，让回归动作可以在 NAS 上直接执行。
- 结果：虽然本机仍不能完成真实容器实跑，但仓库已经具备可直接复制到飞牛云主机执行的自动化回归入口；后续只需在 NAS 目录运行 `python -m client.infra.docker.flyinnas_regression ...` 即可得到 PASS / FAIL 结果。

#### 调试条目 019：PowerShell 部署脚本参数名与内建变量冲突

- 现象：首次执行 [deploy_flyinnas.ps1](E:\Project\DouyinLiveRecorder-4.0.7\deploy_flyinnas.ps1) 的 `-Host` 参数时，PowerShell 直接报 `Cannot overwrite variable Host because it is read-only or constant.`。
- 原因：PowerShell 内建存在只读变量 `$Host`，脚本参数名如果也叫 `Host`，在绑定阶段就会和内建变量发生冲突。
- 处理：将 PowerShell 入口参数改为 `-RemoteHost`，内部仍映射到 Python 部署模块的 `--host` 参数，并补做了一次 `-DryRun` 验证。
- 结果：PowerShell 一键部署入口现已可正常解析参数并输出实际将执行的 `scp` / `ssh` 命令。

## 追加模板

### 完成记录模板

```md
### YYYY-MM-DD

#### C-xxx 任务标题

- 做了什么
- 修改了哪些文件
- 如何验证
- 验证结果
```

### 调试记录模板

```md
### YYYY-MM-DD

#### 调试条目 xxx：问题标题

- 现象：
- 原因：
- 处理：
- 结果：
```
