## Why

rot 检测（c0010）把 finding 标成 resolved，但 resolved 只说明 key 不再出现，不说明账单少了钱。finding 里的 monthly_savings_usd 是估算。没有对账，「清理见效」只是叙述。维护者的要求：实验数据、为什么对、怎么验证真的省钱了、数据分析结论，要有细节。

## What Changes

- 新增 `finops_agent/verify_savings.py`：对三个周期（2026-09 基础世界、`next_month.yaml`、`month_after.yaml`）各跑一次 agent（`--no-judge`，共用 state），再用 boto3 查每个周期自己的 Cost Explorer（资源级日度 + 用量类型级月度）。对每条 resolved finding 计算预测、反事实基线、实现节省、实现率、偏差分类、下一期是否保持，并把整张账单的变动精确分解。
- 新增 `docs/SAVINGS_VERIFICATION.md`（中文，所有数字由代码生成）与 `reports/savings-verification.html`。
- 新增 `scripts/verify_savings.sh`（端口 34566 起）与 `finops_agent/test_verify_savings.py`。

## Capabilities

### New Capabilities
- `savings-verification`：用账单核实 resolved finding 的真实节省。

### Modified Capabilities
（无）

## Impact

只新增文件，不改 `__main__.py`、`report.py`、`testenv/`、Makefile、README，不改场景与标准答案。只读：测试服务器的 Cost Explorer 与 agent 输出。不涉及 AWS 写操作，没有需要人工 gate 的动作，也不需要回滚。make 目标由集成 change 之后添加。
