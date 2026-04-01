# 已知问题

最后更新：2026-04-02

## 已确认问题
- `ffmpeg` 已安装但当前 shell PATH 未自动生效
  - 现象：`winget list --id Gyan.FFmpeg.Essentials` 显示已安装 `8.1`，但直接执行 `Get-Command ffmpeg` 仍报未找到命令。
  - 影响：脚本和手工终端验收时，如果不补 PATH，可能误判为缺少录制依赖。
  - 临时处理：本轮通过显式使用 WinGet 安装目录下的 `ffmpeg.exe`，并在启动命令前把其 `bin` 目录加入当前会话 PATH。
- Git 基线缺失
  - 当前 `git status --short` 显示整仓大量未纳管文件，且 `tmp7qf85p61/`、`tmpbape0idz/` 存在权限告警。
  - 影响：难以直接区分“本轮新增”与“历史遗留”，提交前需要额外审查。
  - 当前状态：`tmp*` 干扰已部分缓解，但真正的版本基线问题仍待 `BL-008` 处理。
  - 进一步确认：当前 `.git/` 存在但无可读 branch / remote / commit 历史，更像是“空仓库初始化后尚未建立首个恢复提交”。
- PowerShell 入口脚本在部分 Windows 会话下会被执行策略拦截
  - 现象：直接执行 `.\deploy_flyinnas.ps1 ...` 可能失败；使用 `powershell -ExecutionPolicy Bypass -File .\deploy_flyinnas.ps1 ...` 可正常进入脚本。
  - 影响：如果忽略执行策略差异，容易误判为 Docker / NAS 部署脚本本身不可用。
  - 临时处理：在文档和验证记录中统一使用 `powershell -ExecutionPolicy Bypass -File ...` 作为 PowerShell 入口示例。
- 根目录存在多组 `tmp_*` 目录
  - 例如：`tmp_history_*`、`tmp_notify_*`、`tmp_scheduler_*`、`tmp_task_store_log_*`
  - 影响：会干扰版本管理、目录扫描与交接理解。
  - 当前状态：已新增 `.gitignore` 规则 `tmp*/` 与 `scripts/cleanup_tmp_artifacts.ps1`；但仓库本地目录尚未统一物理删除。
- 配置文件可能包含敏感信息
  - `config/config.ini` 可能承载 Cookie、代理、通知相关配置。
  - 影响：补文档、建示例配置或共享仓库时必须先脱敏。
  - 当前状态：已新增 `config/config.example.ini` 与 `config/URL_config.example.ini` 作为脱敏样板，但真实 `config/config.ini` 仍需严格本地保存。
- 客户端平台覆盖明显小于 README 主程序总表
  - 现象：README 旧版主程序当前列出 `51` 个平台，而 `client/core/platform_router.py` / `client/core/stream_resolver.py` 仅能确认 `13` 个平台 + 自定义直链。
  - 影响：如果不显式区分，容易把旧版主程序的完整平台能力误读为客户端现状。
- 历史发布说明仍有信息缺口
  - 现象：当前仓库可以恢复当前版本的打包脚本、manifest、sha256 和 `dist` 产物，但缺少可靠 Git 基线来反推完整 changelog。
  - 影响：后续如果要补完整 Release Notes，只能把“仓库可证据部分”与“外部发布页补证部分”拆开处理。

## 已确认但已缓解
- Docker 构建过程偶发 Debian 源 `502 Bad Gateway`
  - 现象：执行 `docker compose -f docker-compose.flyinnas.yaml up -d --build` 时，`apt-get install` 可能因 Debian 源瞬时错误失败。
  - 处理：已在 `Dockerfile` 中加入显式 `apt` 重试循环。
  - 当前状态：2026-04-01 本机重跑后已成功构建并通过健康检查，且 `first-deploy` / `upgrade-deploy` / `rollback-deploy` 三个本机回归场景均已通过；后续仍需观察 NAS 宿主机网络环境。

## 推断问题
- 平台支持清单与客户端实际验证范围之间可能存在差距
  - `BL-005` 已补出第一版平台矩阵，但虎牙、斗鱼、YY、B站等平台当前仍偏“已接线、证据不足”。
- Docker / NAS 文档在不同终端环境下可能存在编码表现差异
  - 当前 PowerShell 读取部分中文文档时有乱码现象，更像是终端编码问题，不一定是文件内容损坏。

## 待确认问题
- 飞牛云 / NAS 主机是否存在额外权限、挂载或网络差异，导致回归结果与 Windows 本机 Docker 不一致；当前仍缺真实宿主机截图、命令输出和部署结果。
- 客户端 GUI 二轮人工冒烟后，是否还会暴露任务状态联动、日志滚动或历史落档的边缘问题。
- 虎牙、斗鱼、YY、B站的客户端解析分支是否应被视为“当前可发布支持”还是“仍需补证据后再宣称支持”。
- 示例配置是否需要进一步自动校验与真实配置字段保持同步，避免后续新增字段时再次失配。
- 历史 Release 页面文案、上传记录与发布时间线是否还能从外部来源补回。
- `tmp7qf85p61/`、`tmpbape0idz/` 这类无权限空目录的来源与最稳妥清理方式仍待确认。
- `deploy/` 空目录是否属于无效遗留项，仍待确认是否删除。
