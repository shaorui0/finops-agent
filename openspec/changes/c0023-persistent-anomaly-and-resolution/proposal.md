## Why

c0015 的样本外评估暴露了两个可信度缺口（evidence.md E5 / E6 / E14）：

1. **窗口开始前就存在的费用异常没有线索。** `leads_from_cost_shape` 只比较窗口前 3 天和最后 7 天。2026-09-04 起的 NAT 放大在 10 月、11 月窗口里「前 3 天已经是涨后水平」，没有跳变，没有线索，GT02 在两个样本外世界都漏了（recall 0.9 / 0.9091，savings_recall 0.566）。
2. **没再检出被记成 resolved。** `diff_state` 只看 finding 在不在，不在就写 resolved。漏检因此伪装成修复（E14）。`regressed` 又建立在 resolved 之上，所以也会被污染。

## What Changes

- **持续异常线索**：快照多取窗口前 92 天的 DAILY by USAGE_TYPE（`cost_history_daily_by_usage_type`）。对窗口内中位数超过历史 P25 基线 2 倍、且没有产生跳变线索的用量类型，出一条 `cost_growth` 线索，`since` 取历史里第一个超过 2 倍基线的日子。这条线索排在其他线索之后，已有线索的 id、文字、证据、参数不变。
- **resolved 与 not_redetected**：`diff_state` 对消失的 finding 查成本侧证据（资源是否还在清单里、属性是否变了、近 14 天日均成本是否掉了 10% 以上）。资源没了或变了才是 `resolved`；还在且没变是 `not_redetected`，不进 `resolved` 表，所以之后再出现也不叫 `regressed`。`finops_findings{state="not_redetected"}` 自动出现。无快照的旧调用保持旧行为。
- **样本外污染声明**：这次修复针对的是样本外世界上看到的失败。`eval/EXPERIMENTS.md` 新增一节说明改了什么、前后数字、为什么这两个世界对这个失败已不再是样本外。

## Capabilities

### New Capabilities
- `persistent-anomaly-and-resolution`：窗口前就存在的费用异常有线索；消失的 finding 区分已解决与未再检出。

### Modified Capabilities
（无）

## Impact

`finops_agent/analyze.py`、`collect.py`（多一次 Cost Explorer 只读调用）、`slo.py`、各自测试、`eval/heldout.py`（端口范围可由环境变量覆盖）、`eval/test_heldout.py`、`eval/EXPERIMENTS.md`、`docs/FINOPS_SLO.md` 的 Rot 一节、`eval/cassettes/`（只新增 6 个）。基础世界 7 个 cassette 键不变。录制 6 次调用，$0.1845。AWS 只读不受影响，不涉及写操作。
