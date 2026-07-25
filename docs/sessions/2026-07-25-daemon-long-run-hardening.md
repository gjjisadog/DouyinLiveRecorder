# daemon 长期运行加固

日期：2026-07-25

## 范围

- 仅加固 Docker 抖音 daemon 的调度、HTTP 连接、健康状态和 FFmpeg 生命周期。
- 未修改抖音解析算法、Windows GUI、旧多平台入口或 NAS Web 业务功能。

## 修改

- 单一 `asyncio` 调度循环和逐房间任务，慢房间不阻塞其他房间。
- 逐房间连续失败、指数退避、随机抖动与成功重置。
- daemon 作用域共享 `httpx.AsyncClient` 连接池并在退出时关闭。
- HealthState 线程/异步并发保护和唯一临时文件原子写。
- FFmpeg 滑动窗口健康统计、累计/连续崩溃与最近成功时间。
- HLS/FLV 分协议重连、超时和损坏流容错。
- 24/72 小时采样脚本及操作文档。

## 验证

- 全仓 `python -m pytest -v`：161 项通过，覆盖调度并发、客户端复用/关闭、逐房间退避、
  HealthState 并发、滑动窗口、HLS/FLV 命令、FFmpeg 停止和 TS `ffprobe`。
- 三份 Compose 配置解析通过；`daemon` 与 `nas-web` target 真实构建通过。
- Docker 双模式运行烟雾通过：NAS Web 鉴权、YAML 热加载、共享健康状态、
  SIGINT 停止、无残留 FFmpeg 和最后 TS `ffprobe`。
- 默认 Compose 达到 healthy；`docker stop douyin-recorder` 后容器
  `Running=false`、`Pid=0`、`ExitCode=0`，日志包含 `daemon_stopped`。

## 未执行

- 未跑满真实 24/72 小时。
- 未在真实 ARMv7 NAS 上做长期录制。
