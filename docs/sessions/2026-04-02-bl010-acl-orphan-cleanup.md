# 2026-04-02 BL-010 ACL Orphan Cleanup

## 这次做了什么
- 复核了根目录下两个异常目录：
  - `tmp7qf85p61/`
  - `tmpbape0idz/`
- 再次确认当前会话下无法读取 ACL、也无法直接删除。
- 补了一份管理员终端专用清理脚本，避免下次再手敲长命令。

## 已确认
- 两个目录当前仍存在于仓库根目录。
- 当前普通会话执行：
  - `icacls tmp7qf85p61`
  - `icacls tmpbape0idz`
  都返回 `Access is denied.`
- 当前普通会话执行：
  - `Remove-Item -LiteralPath .\tmp7qf85p61 -Recurse -Force`
  - `Remove-Item -LiteralPath .\tmpbape0idz -Recurse -Force`
  均返回拒绝访问。

## 新增文件
- 管理员清理脚本：`scripts/remove_acl_orphans_admin.ps1`

## 使用方式
- 在“管理员 PowerShell”中进入仓库根目录后执行：
  - `powershell -ExecutionPolicy Bypass -File .\scripts\remove_acl_orphans_admin.ps1`
- 如需先演练：
  - `powershell -ExecutionPolicy Bypass -File .\scripts\remove_acl_orphans_admin.ps1 -WhatIf`

## 脚本行为
- 只处理两个固定目录名，不会扫描或删除其他路径。
- 会按顺序执行：
  - `takeown`
  - `icacls /grant Administrators:F`
  - `attrib -R -S -H`
  - `rd /s /q`
- 删除后会再次检查目录是否仍存在；若还在则直接报错。
- 当前已确认：
  - `-WhatIf` 演练模式可正常解析仓库根路径并列出两个目标目录。

## 结论
- `BL-010` 目前已收敛到“需要管理员终端执行一次清理脚本”。
- 这不是业务代码问题，也不是普通开发会话内能继续推进的问题。
