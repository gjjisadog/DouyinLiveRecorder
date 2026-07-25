# daemon 长期运行增强与 NAS 观察

日期：2026-07-25

## 本轮实现

- 新增稳定主播身份缓存，优先使用主播 `sec_uid`，再回退到房间标识。
- 新增默认关闭、最大 4 并发的 TS 到 MP4 流复制队列。
- 新增旧版 `URL_config.ini` / `config.ini` 安全迁移入口，Cookie 单独输出。
- 新增解析失败观察文件 `error_observations.json`：仅保留分类、异常类型、
  脱敏摘要和指纹，最多 50 条。

## 验证

- daemon 定向测试 34 项通过，其中包含真实 FFmpeg TS 到 MP4 remux 及 ffprobe。
- 全仓回归 140 项通过。
- ARMv7 使用真实 buildx/QEMU 完成镜像构建；容器内验证为 `armv7l`，
  FFmpeg 5.1.9、Node 18.20.4、Python/ExecJS 与 daemon 导入正常。

## NAS 观察约束

- 使用隔离目录 `/vol1/docker/douyin-daemon-24h`，不修改旧项目或旧容器。
- NAS 首次启动暴露了 root 迁移后 `600` Secret 与非 root daemon 的属主冲突；
  已改为支持 `--cookie-uid 10001`，以 root 迁移时输出 UID 10001、`0400` 文件。
- 旧配置仅有 1 个启用房间；09:48 从抖音公开热门页选择并实时解析验证 2 个
  正在直播的测试房间，以 SD 画质补入隔离配置。
- 观察结果需包含容器健康、录制结果、磁盘、Cookie/风控分类计数，不记录 Cookie
  或完整直播间 URL。

## 观察启动记录

- 最终镜像观察起点：2026-07-25 08:58（Asia/Shanghai）；08:54 的首版实例在
  修正 Secret 权限和强化样本脱敏后滚动替换，状态卷保留。
- 镜像：`douyin-recorder:nas-24h`，AMD64，运行用户 UID/GID 10001。
- 首轮状态：容器 healthy，状态检查完成，解析失败 0，活动录制 0。
- Secret：UID 10001、模式 `0400`；只记录元数据，不记录内容。
- 旧 `douyin-live-recorder` 仍为三个月前的 exited 状态。
- daemon 24 小时检查点：2026-07-26 08:58（Asia/Shanghai）。
- 多房间 24 小时检查点：2026-07-26 09:48（Asia/Shanghai）。
- 09:50 多房间复核：配置 3 个房间，2 个 FFmpeg 进程持续写入；
  `active_recordings=2`、解析失败 0、容器 healthy、重启 0。
