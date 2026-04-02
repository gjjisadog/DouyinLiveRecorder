# 2026-04-02 配置示例同步校验落地

## 本次做了什么
- 新增公开配置样板同步校验模块：`client/infra/config_example_sync.py`
- 新增可直接执行的检查脚本：`scripts/check_config_examples.py`
- 新增回归测试：`client/tests/test_config_example_sync.py`
- 更新 `README.md` 与 handover，明确后续如何自检示例配置未落后于真实配置

## 已确认
- 当前 `config/config.example.ini` 的 section/key 没有落后于 `config/config.ini`
- 当前 `config/URL_config.example.ini` 至少保留了一条非注释示例地址
- 检查脚本可直接执行：
  - `& '.\.client-conda-env\python.exe' scripts/check_config_examples.py`
- 回归测试已通过：
  - `& '.\.client-conda-env\python.exe' -m unittest client.tests.test_config_example_sync -v`

## 设计边界
- 当前校验目标是“公开样板不落后于真实配置”
- 因此默认只要求：
  - `config/config.example.ini` 至少覆盖 `config/config.ini` 的全部 section/key
  - `config/URL_config.example.ini` 至少保留一条可见示例地址
- 当前不限制示例文件是否存在额外说明性字段，也不检查敏感值内容本身

## 下一次继续建议
- 如后续又新增真实配置字段，先运行一次：
  - `& '.\.client-conda-env\python.exe' scripts/check_config_examples.py`
- 如要继续执行 backlog，当前更适合转向：
  1. 管理员终端清理 `tmp7qf85p61/`、`tmpbape0idz/`
  2. 补客户端“虎牙 / 斗鱼 / YY / B站”专项回归证据
