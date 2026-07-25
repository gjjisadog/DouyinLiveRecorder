# 抖音 Docker daemon 服务化

日期：2026-07-24

## 目标

在不改变原有多平台 CLI 和 Windows 客户端入口的前提下，增加适合 NAS /
Linux 长期无人值守运行的抖音专用录制服务。

## 主要决策

- Docker 使用独立 `app.douyin_daemon`，不向 `main.py` 继续添加容器分支。
- 解析复用 `src.spider` 和 `src.stream`；daemon 只负责配置、调度和生命周期。
- 默认输出分段 TS 并使用 `-c copy`，不自动转 MP4、不重新编码、不删除源文件。
- 所有 FFmpeg 由统一注册表管理；停止顺序为 SIGINT、terminate、kill。
- Cookie 首选 Docker Secret 文件，日志只记录脱敏状态。
- TLS 证书校验恢复为 HTTP 客户端默认行为。
- 正式镜像目标为 AMD64 与 ARM64；ARMv7 暂不承诺。

## 验证

- 新增配置、URL、Cookie、画质/协议、重试和 FFmpeg 命令单元测试。
- 新增本地合成音视频流集成测试：中断 FFmpeg 后用 `ffprobe` 验证 TS。
- 保留并运行原有客户端测试，确认多平台与 GUI 主线没有被替换。
