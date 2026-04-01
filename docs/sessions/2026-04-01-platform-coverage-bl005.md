# 2026-04-01 Platform Coverage BL-005

## 本次做了什么
- 从 `docs/handover/executable_backlog.md` 接手 `BL-005`“平台接入覆盖复核”。
- 核对了 `README.md` 中旧版主程序的“已支持平台”清单。
- 核对了客户端平台接入主入口：
  - `client/core/enums.py`
  - `client/core/platform_router.py`
  - `client/core/stream_resolver.py`
- 核对了和平台证据最相关的客户端测试：
  - `client/tests/test_platform_migration.py`
  - `client/tests/test_task_import_export.py`
  - `client/tests/test_task_viewmodel.py`
  - `client/tests/test_settings_page.py`
  - `client/tests/test_core_services.py`
- 重新执行了：
  - `client.tests.test_platform_migration`
  - `client.tests.test_task_import_export`
  - `client.tests.test_task_viewmodel`
  - `client.tests.test_settings_page`
  共 `18` 项测试，结果全部通过。
- 将“客户端当前已迁移平台”与“自动化验证范围”补写回 `README.md` 与 handover。

## 关键命令
```powershell
& '.\.client-conda-env\python.exe' -m unittest client.tests.test_platform_migration -v
& '.\.client-conda-env\python.exe' -m unittest client.tests.test_task_import_export client.tests.test_task_viewmodel client.tests.test_settings_page -v
```

## 已确认结果
- 旧版主程序 README 当前列出 `51` 个已支持平台。
- 客户端当前已接入 `client/core/platform_router.py` 与 `client/core/stream_resolver.py` 的平台为：
  - 抖音
  - TikTok
  - 快手
  - 虎牙
  - 斗鱼
  - YY
  - B站
  - 网易 CC
  - 千度热播
  - PandaTV
  - 百度直播
  - ShowRoom
  - CHZZK
  - 以及自定义 `m3u8` / `flv` 直链
- 自动化证据可分为四层：
  - 路由识别已确认：
    - 网易 CC
    - 千度热播
    - PandaTV
    - 百度直播
    - ShowRoom
    - CHZZK
  - 解析分支已确认：
    - 网易 CC
    - CHZZK
  - 任务导入 / 展示 / 持久化已确认：
    - 抖音
    - TikTok
    - 快手
    - ShowRoom
    - CHZZK
  - `ffmpeg` / 录制相关已确认：
    - 抖音（选流逻辑）
    - PandaTV（代理 / Header 构建）
    - 自定义 `m3u8` 直链（来自 `BL-002` 真实烟测）

## 推断
- 虎牙、斗鱼、YY、B站当前大概率已经完成客户端接线，因为：
  - 它们存在于 `Platform` 枚举
  - 存在于 `PLATFORM_RULES`
  - 存在于 `StreamResolver.resolve_task()` 分支
- 但当前仓库内尚未看到它们对应的客户端专用解析回归，因此不能仅凭接线就视为“客户端已充分验证”。

## 本次未完成
- 还没有补出“虎牙 / 斗鱼 / YY / B站”四个平台的客户端专用解析或录制回归。
- 还没有把客户端平台矩阵单独拆成长期维护文档；目前先落在 handover / session / README 中。

## 结论
- `BL-005` 本轮已经完成：客户端平台覆盖边界已从“模糊印象”收敛为“代码接入范围 + 自动化证据范围 + 待补证据范围”。
- 当前最重要的边界结论是：
  - **不能**再把 README 的 `51` 平台总表直接当作客户端现状
  - 客户端当前能明确确认的是 `13` 个平台 + 自定义直链
  - 其中“已接线”与“已验证”仍是两回事
- 如果后续继续补平台证据，优先顺序建议为：
  1. 虎牙
  2. 斗鱼
  3. YY
  4. B站
