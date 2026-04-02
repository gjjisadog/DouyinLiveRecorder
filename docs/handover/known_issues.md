# 已知问题

最后更新：2026-04-02

## 已确认问题
- 本机 `ffmpeg` 已安装，但当前 shell 的 PATH 不稳定，脚本执行时仍应显式补 PATH 或传入 `FFMPEG_DIR`。
- 根目录仍有两个 ACL 异常目录：
  - `tmp7qf85p61/`
  - `tmpbape0idz/`
  当前普通会话无法删除，需管理员终端处理。
  已补管理员脚本：`scripts/remove_acl_orphans_admin.ps1`
- 外部 UIAutomation / `pywinauto` 对打包版 Qt 的按钮触发仍不稳定：
  - 能识别主窗口和控件树
  - 但不适合作为当前主验收方案

## 已缓解
- 打包版 EXE 的核心录制自动化已由“外部点控失败”切换到“进程内文件桥成功”。
- 历史上的 `Cannot log to objects of type 'NoneType'` 在当前重打包后未再复现。
- `scripts/exe_automation_acceptance.py` 已补上录制产物校验，降低“假通过”风险。

## 推断风险
- 若后续频繁改动 `client/ui/main_window.py` 的自动化命令分支，而没有同步更新验收脚本，文件桥可能出现接口漂移。
- 若长期继续依赖人工点击验证，容易与当前“文件桥自动化已可用”的事实重复投入。

## 待确认
- 是否仍要求真人手点 EXE 作为发布门槛。
- 是否需要把文件桥进一步抽成更正式的调试/验收接口，并写入 README 或客户端验收文档。
