# 客户端存储策略

最后更新：2026-03-31

## 当前结论

- 当前客户端继续以 JSON 作为主存储。
- SQLite 不作为现阶段业务主存储，但作为已初始化的迁移基座保留。
- 存储决策会在启动时写入 `client_data/storage_meta.json`，并同步初始化 `client_data/client.db` 的基础元信息表。

## 为什么现在不直接切 SQLite

- `config.json`、`tasks.json`、`history.json` 当前数据量仍小，直接查看、备份、手工修复都更简单。
- 现有客户端已经围绕 JSON 建立了容错、坏文件隔离和旧版配置兼容测试，贸然切库会扩大回归面。
- 现阶段最需要的是“明确边界和迁移入口”，而不是把所有存储一次性改写。

## 存储边界

| 领域 | 当前后端 | 文件 | 说明 |
| --- | --- | --- | --- |
| 配置 | JSON | `client_data/config.json` | 用户配置量小，人工排查和兼容旧版 `config.ini` 更方便 |
| 任务 | JSON | `client_data/tasks.json` | 当前任务规模可控，且仍需兼容旧版 `URL_config.ini` 导入导出 |
| 历史 | JSON | `client_data/history.json` | 当前查询维度简单，优先保留现有稳定链路 |
| 迁移基座 | SQLite | `client_data/client.db` | 为未来历史索引、检索、统计和结构化迁移预留基础设施 |

## 已落地能力

- 启动时自动写出 `storage_meta.json`，记录当前模式、边界和迁移计划。
- 启动时自动初始化 `client.db`，创建 `app_metadata` 与 `migrations` 表。
- SQLite 基座会写入 `schema_version`、`initialized_at`、`last_initialized_at`，为后续迁移做版本管理准备。

## 后续迁移顺序

1. 保持 `config/tasks/history` 继续使用 JSON，观察 `history.json` 的增长规模和加载成本。
2. 如果历史记录开始影响加载、筛选或统计，优先把“历史索引与查询”迁移到 SQLite。
3. 只有在任务查询、批量编辑、跨页联动变复杂时，再评估 `tasks` 是否需要进入 SQLite。
4. `config` 最后评估，除非出现复杂事务、加密或多来源合并需求，否则继续保留 JSON。

## 判断迁移时机的信号

- `history.json` 加载明显拖慢启动或页面刷新。
- 需要按时间范围、平台、状态做复杂组合筛选。
- 需要统计报表、分页、聚合查询。
- 需要更稳定的 schema version 管理和批量迁移脚本。

## 相关代码

- [storage_strategy.py](E:\Project\DouyinLiveRecorder-4.0.7\client\infra\storage\storage_strategy.py)
- [sqlite_repo.py](E:\Project\DouyinLiveRecorder-4.0.7\client\infra\storage\sqlite_repo.py)
- [bootstrap.py](E:\Project\DouyinLiveRecorder-4.0.7\client\bootstrap.py)
- [app_settings.py](E:\Project\DouyinLiveRecorder-4.0.7\client\app_settings.py)
