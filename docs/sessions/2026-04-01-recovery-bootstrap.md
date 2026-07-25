# 2026-04-01 仓库恢复引导

## 已检查

- `README.md`
- `main.py` 与 `src/`
- `client/main.py`、`client/bootstrap.py` 与 `client/core/`
- Dockerfile、Compose、构建脚本和测试目录

## 恢复结论

- 仓库保留旧多平台 CLI，同时建设 PySide6 客户端。
- 客户端通过 `client/core/stream_resolver.py` 复用旧解析模块。
- Docker/NAS 是独立部署边界，需要单独的入口、健康检查与持久化验证。
- 恢复资料由 architecture、handover、ADR 和 session 四类文件组成。

## 证据边界

- 当时的客户端测试和编译检查已在对应任务中执行。
- Docker 真机构建、NAS 长时间运行和公开网络流验证必须由后续独立记录提供，不从本次恢复过程推断。
