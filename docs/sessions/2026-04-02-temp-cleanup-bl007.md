# 2026-04-02 Temp Cleanup BL-007

## 本次做了什么
- 从 `docs/handover/executable_backlog.md` 接手 `BL-007`“临时目录清理策略”。
- 盘点了根目录所有 `tmp*` 目录。
- 按“是否被 session 文档引用、是否含真实取证产物”对这些目录做了分类。
- 新增 `scripts/cleanup_tmp_artifacts.ps1`，用于安全 dry-run / 分阶段清理。
- 更新 `.gitignore`，新增 `tmp*/`，避免临时目录继续污染版本基线。

## 已确认结果
- 当前根目录可见 `20` 个 `tmp*` 目录。
- 其中最明确需要默认保留的是：
  - `tmp_bl002_record_smoke`
    - 原因：包含真实录制文件、`history.json`、`tasks.json`、`client.db`
    - 且已被 `docs/sessions/2026-04-01-client-bl002-smoke.md` 直接引用
- 其余大多数目录更像测试 / 调试残留：
  - `tmp_config_log_*`
  - `tmp_history_*`
  - `tmp_notify_*`
  - `tmp_scheduler_*`
  - `tmp_settings_notify_*`
  - `tmp_task_store_log*`
- 发现两类异常目录：
  - `tmp7qf85p61`
  - `tmpbape0idz`
  - 当前扫描为空目录，但此前 `git status` 曾对它们报权限告警

## 清理策略
- 默认规则：
  - 被 `docs/sessions/` 引用的 `tmp*` 目录视为取证目录，脚本默认保留
  - 未被引用的 `tmp*` 目录视为候选清理对象
- 脚本入口：
  - `scripts/cleanup_tmp_artifacts.ps1`
- 使用方式：
  - 仅查看分类：`.\scripts\cleanup_tmp_artifacts.ps1`
  - 删除未被引用的临时目录：`.\scripts\cleanup_tmp_artifacts.ps1 -Delete`
  - 连取证目录也一起删：`.\scripts\cleanup_tmp_artifacts.ps1 -Delete -IncludeEvidence`

## 本次未完成
- 没有直接物理删除这些目录；本轮重点是先建立安全策略，而不是贸然删证据。
- `tmp7qf85p61`、`tmpbape0idz` 的来源和权限状态还未彻底查清。

## 结论
- `BL-007` 已完成：仓库已经具备“可忽略、可分类、可安全清理”的最小机制。
- 后续如果继续做 `BL-008`，可以在此基础上进一步把 `git status` 噪音收敛下来。
