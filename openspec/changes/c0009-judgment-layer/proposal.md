## Why

确定性检测器只能找到"一跳"的发现。当前 eval：recall 7/12，deep recall 0.44，savings recall 0.19。漏掉的 5 条（忙但无用的 ingest fleet、被重试放大的 NAT、跨 AZ 流量、被 Savings Plan 吃掉的 dev 调度节省、夜间 ETL 常开）都要跨三到四个数据源判断，检测器只能把它们留作线索（leads）。线索一直是线索，没人回答。

## What Changes

- 新增判断层 `finops_agent/judge/`：每条线索先由代码取证并**算出**候选数字（fleet 成本、成功率、NAT 多出的 GB 与金额、跨 AZ GB、Savings Plan 对空闲时段的吸收），再交给 LLM 判断。LLM 只能从候选里选数字（FA03），资源必须来自白名单，文本里的数字必须能在证据里找到，否则判断被拒绝并写入 trace。
- 新增确定性线索生成器：按小时 CPU 找出只忙一部分时间的非 ASG 实例（dev 调度、夜间 ETL、DR 温备），这些线索此前根本不存在。
- 新增 `finops_agent/llm.py`：record / replay / live 三种模式的 LLM 客户端。默认 replay，从提交进仓库的 cassette 读取，CI 与 `make eval` 不需要网络和 API key。
- 每条线索一次独立调用（FA11 上下文隔离），并发执行。
- trace 记录每次调用的 tokens、延迟、花费；报告新增「Agent 成本」一节，线索卡片显示判断结论。
- `eval/baseline.json` 在新指标通过后重写。

## Capabilities

### New Capabilities
- `judgment`：线索 → 取证 → 判断 → 发现的契约与校验规则。
- `llm-client`：record / replay / live 与 cassette 约定。

### Modified Capabilities
（无）

## Impact

流水线多出一步，默认 replay 所以离线可复现。`Lead` 增加 `kind` 与 `params` 字段。`test_pipeline` 的"只读"断言只针对 AWS / Prometheus 调用。本 change 不接入修复建议（c0011），也不改 testenv。
