# 2026-04-04 发布前验收说明收口

## 本次做了什么
- 依据已完成的 `BL-019` 与 `BL-017`，把分散在 handover / session / 临时产物中的结果回填到 `CLIENT_RELEASE.md`。
- 明确写入当前发布前可直接引用的两条关键证据：
  - `1 GB` 按大小自动切段
  - 打包版 `get_logs` 稳定性
- 同时把当前仍保留的边界写清楚，避免后续误把“本地连续流样本”表述成“外部长时真实业务流样本”。

## 本次引用的关键证据
- `tmp_bl019_local_source_1gb_run1/acceptance_summary.json`
- `tmp_bl017_get_logs_stability_run1/acceptance_summary.json`
- `tmp_bl017_get_logs_stability_run3/acceptance_summary.json`
- `tmp_bl017_get_logs_stability_run4/acceptance_summary.json`
- `docs/sessions/2026-04-03-bl019-test-source-switch.md`
- `docs/sessions/2026-04-04-bl017-get-logs-stability.md`

## 已写入发布文档的结论
- `1 GB` 自动切段：
  - 已在本地连续 HLS 源下通过
  - 最大超限 `1867840` bytes，约 `0.17%`
  - 当前决策是不再继续微调 `1 MB` 安全余量
- `get_logs` 稳定性：
  - 本地连续流样本下累计 `105/105` 成功
  - 未复现 `BL-013` 中的超时
  - 已观测最大延迟 `406.09ms`

## 仍保留的边界
- 当前最强证据仍然是本地连续 HLS 样本，不是外部长时真实业务流。
- 如果后续要补更强的发布背书，下一步应是外部长时源对照样本，而不是重复本地源样本。

## 下一次继续时建议
1. 如果准备收口发布，就直接引用 `CLIENT_RELEASE.md` 中新增的“发布前验收收口（2026-04-04）”章节。
2. 如果准备继续补证，则优先外部长时直播源对照，不再重复本地 HLS 方案。
