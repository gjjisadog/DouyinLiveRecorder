# 2026-04-02 Git Baseline BL-008

## 本次做了什么
- 从 `docs/handover/executable_backlog.md` 接手 `BL-008`“Git 状态基线恢复”。
- 核对了当前 Git 元数据：
  - `.git/` 存在
  - `git rev-parse --is-inside-work-tree` 返回 `true`
  - 当前无 branch / remote / commit 历史可读输出
  - `.git/config` 仅包含基础 `core` 配置
- 重新查看 `git status --short --ignored`，确认当前是“已初始化但零提交基线”的状态，而不是“正常项目上叠加少量改动”。
- 盘点了顶层目录，按“应纳管源码 / 本地产物 / 待确认孤儿目录”做了分类。
- 更新 `.gitignore`，补充：
  - `client_data/`
  - `tmp_*.log`
- 新增 `scripts/show_git_baseline_scope.ps1`，输出建议纳管路径、已忽略产物范围和首个恢复提交前应再次人工确认的孤儿目录。

## 已确认结果
- 当前 Git 现场可确认：
  - 仓库已 `git init`
  - 但没有可用 commit 历史
  - 没有配置 remote
  - 因此当前无法从 Git 侧恢复“上游基线”
- 当前建议纳管的源码 / 文档目录：
  - `.agents/`
  - `.codex/`
  - `.github/`
  - `client/`
  - `config/`（但以示例文件和模板为主，真实敏感配置需谨慎）
  - `docs/`
  - `i18n/`
  - `prompts/`
  - `scripts/`
  - `src/`
  - 以及根目录下的 `README.md`、`AGENTS.md`、`CLIENT_*.md`、`DOCKER_*.md`、`Dockerfile`、`docker-compose*.yaml`、`requirements*.txt`、`main.py`、`msg_push.py`、`ffmpeg_install.py`、`start_client.*`、`build_*`
- 当前应视为本地产物 / 运行产物的目录：
  - `.client-conda-env/`
  - `build/`
  - `dist/`
  - `downloads/`
  - `logs/`
  - `backup_config/`
  - `client_data/`
  - `tmp*/`
  - `tmp_*.log`
- 当前待确认的孤儿项：
  - `deploy/`：顶层为空目录，当前仓库内没有有效内容
  - `tmp7qf85p61/`、`tmpbape0idz/`：空目录但伴随权限告警

## 推断
- 当前更像“项目文件还在，但版本控制历史丢失后又重新初始化了一个空 Git 仓库”。
- 在这种前提下，`BL-008` 现阶段最合理的目标不是“伪造历史”，而是先恢复：
  1. 忽略规则
  2. 纳管范围
  3. 后续最小提交基线

## 本次未完成
- 没有直接执行 `git add` / `git commit`，因为这会真正写入一个新基线，属于需要明确决策的动作。
- 没有处理 `deploy/`、`tmp7qf85p61/`、`tmpbape0idz/` 的物理删除。

## 结论
- `BL-008` 已完成“基线恢复前半段”：Git 现场已被澄清，源码范围与产物范围已被明确。
- 下一步如果要真正建立可持续的 Git 基线，建议顺序是：
  1. 先清掉确认无用的孤儿目录
  2. 再按“源码 / 文档 / 模板 / 脚本”建立首个最小提交基线
  3. 之后所有变更再基于这个新基线推进
