---
name: project-memory-handoff
description: Maintain concise architecture, handover, known-issue and session records after repository changes.
---

# Project Memory Handoff

## 适用场景

- 恢复仓库上下文。
- 完成一项可交付功能或修复。
- 记录验证结果、遗留风险和下一步。

## 必读资料

- `AGENTS.md`
- `docs/architecture/overview.md`
- `docs/handover/current_status.md`
- `docs/handover/next_steps.md`
- `docs/handover/known_issues.md`
- 与当前任务直接相关的 `docs/sessions/` 记录。

## 收尾流程

1. 依据代码、测试输出和 Git 历史区分已确认、推断和未知。
2. 在 `current_status.md` 记录当前可运行状态和本次验证。
3. 在 `next_steps.md` 只保留尚未完成且仍有价值的后续工作。
4. 在 `known_issues.md` 记录未解决风险、影响和缓解方式。
5. 新增一份 `docs/sessions/YYYY-MM-DD-<topic>.md`，写明范围、修改、验证与未执行项。
6. 仅在架构边界变化时更新 `docs/architecture/overview.md` 或 ADR。

## 质量要求

- 使用 UTF-8 和仓库相对路径。
- 不记录本机绝对路径、秘密、Cookie 或令牌。
- 不把计划写成已完成事实。
- 不声称完成未实际执行的长时间、真机或网络验证。
- 不复制与当前任务无关的大段历史。
