## Why

`eval/EXPERIMENTS.md` 第 6 节承认：`next_month`、`month_after` 两个样本外世界被用来发现并修复了 GT02 的漏检（c0023），它们的 1.0 已不再是泛化估计。基础世界的 1.0 是样本内的。现在没有一个未被污染的数字。

## What Changes

- 新建一个**全新的完整世界** `testenv/heldout/fresh_world.yaml`（不是覆盖层）：不同的公司形态（货运追踪 SaaS）、服务与团队命名、区域 eu-west-1、实例家族、数量级和资源布局；12 条标准答案、6 个陷阱（含 1 个 metadata 注入）、3 个可见性缺口。
- **预注册**：先提交世界、标准答案、评估命令、要报的指标和决策规则（commit A）；之后才录制判断层 cassette 并跑一次评估（commit B）；结果原样记录并分析（commit C）。提交顺序是证据。
- `eval/heldout.py` 加入该世界并标记 `preregistered`；`eval/test_heldout.py` 钉住新数字；`eval/EXPERIMENTS.md` 追加第 7 节。

## Decision rule（预注册，详见 prereg.md）

不根据这次结果改任何 agent 代码或 prompt。发现的失败只记录，进下一个 change 的输入，且那之后这个世界同样会被污染，需要再造一个。

## Capabilities

### New Capabilities
- `fresh-heldout`：一个预注册、只评估一次的新样本外世界，及其评估入口。

### Modified Capabilities
（无）

## Impact

只新增 `testenv/heldout/`、`eval/cassettes/`（只新增，预算 ≤ 12 次调用）、`openspec/changes/c0024-fresh-heldout/`、报告与笔记；修改 `eval/heldout.py`、`eval/test_heldout.py`，`eval/EXPERIMENTS.md` 只追加第 7 节。不改 `world.py`、`analyze.py`、`judge/`、任何 agent 代码或 prompt，不改已有 cassette。AWS 只读不受影响，不涉及写操作。
