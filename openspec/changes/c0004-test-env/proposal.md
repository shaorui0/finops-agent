## Why

先不接真实账号，但整条链路要能跑。需要一个能代替 AWS 和 Prometheus 的测试环境，并且测试数据要足够深：浪费藏在多个数据源的交叉处，一环扣一环，还要有看起来像浪费、实际不是的陷阱。否则 agent 学到的只是"找闲置资源"，这不是 FinOps。

## What Changes

- `testenv/world.yaml`：一个合成账号，约 $8.7K/月；12 条 ground-truth finding（每条标 `method_step` 与推理跳数），4 个陷阱，3 个可见性缺口。
- `testenv/world.py`：从 world.yaml 推导逐日成本行（含 Savings Plan 摊销）与指标形状。
- `testenv/aws_server.py`（test-aws-server）：用 botocore 自己的 service model 序列化响应，boto3 和 aws CLI 原样可用；写操作一律 `UnauthorizedOperation`；可记录每次 API 调用。
- `testenv/metrics_server.py`（test-metrics-server）：Prometheus HTTP API + PromQL 子集。
- `docs/METHOD.md`：维护者的成本优化方法（运营级 vs 架构级，M0–M6 七步），作为 agent 的作业顺序。
- `tools/check_rules.py`：账号号规则放过全同数字占位符与资源 ID 后缀。

## Capabilities

### New Capabilities
- `synthetic-world`：合成账号与 ground truth 的结构和自洽约束。
- `test-aws-server`：只读、协议兼容的 AWS 假服务。
- `test-metrics-server`：Prometheus 兼容的指标假服务。

### Modified Capabilities
（无）

## Impact

新增 `testenv/`、`requirements.txt`（boto3、PyYAML）。不碰真实 AWS。
