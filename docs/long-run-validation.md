# Docker daemon 24/72 小时验证

此脚本只提供可重复执行的验证流程；仓库不预置、也不声称已经完成 24/72 小时实测。

准备有效的 `config/douyin.yaml` 与 Cookie secret 后，在仓库根目录执行：

```bash
python scripts/docker_long_run_validate.py --hours 24 --interval 60 --stop-at-end
python scripts/docker_long_run_validate.py --hours 72 --interval 60 --stop-at-end
```

结果写入 `artifacts/long-run/<时间戳>/`：

- `samples.jsonl`：每次采样的容器重启数、房间检查成功率、FFmpeg 崩溃、网络错误分类、活动录制数、CPU、内存、磁盘占用和 FFmpeg 进程数。
- `summary.json`：重启增量、最终成功率、累计崩溃、磁盘增长、最大活动录制数、最后一段 TS 的 `ffprobe` 结果，以及停止后的容器 PID/残留进程判定。

脚本自身的短时冒烟可使用：

```bash
python scripts/docker_long_run_validate.py --duration-seconds 120 --interval 10 --stop-at-end
```

长期验收应保留完整输出目录，并结合 `docker compose logs` 审核网络错误和风控样本。真实时长未跑满时，结果只能标记为“进行中”或“未验证”。
