## Why

测试数据的标准答案只有 id、跳数和节省区间，人读不出「现在什么样、应该什么样、差在哪、怎么处理、怎么不再发生」。维护者要的是这条完整链路能被看见，也要一张能读的目录页：该画表的画表，该画图的画图。

## What Changes

- `testenv/world.yaml` 的每个 `ground_truth` finding 和 trap 新增五个字段：`status`（现状）、`spec`（期望）、`diff`（差异）、`runbook`（有序处置步骤）、`prevention`（预防）。只加字段，不改任何已有值、资源和节省区间。
- `testenv/scenarios/next_month.yaml`、`month_after.yaml` 的 `scenario.expect` 新增 `details`（每个期望变化同样五个字段）和 `story`（本场景讲了什么、为什么）。
- 文本里的数字用占位符（`{cost:...}`、`{sav:GT06}` 等），由 `testenv/catalog.py` 对着 `testenv.world.load()` 的成本行计算后替换，不手写进散文。
- 新增 `testenv/catalog.py`：`python3 -m testenv.catalog --out reports/testenv-catalog.html` 生成自包含 HTML（总览表、逐 case 卡片、陷阱、腐化时间线、可见性缺口、架构图）。
- 新增 `testenv/test_catalog.py`。

## Capabilities

### New Capabilities
- `testenv-catalog`：测试账号的标准答案以五段式呈现，并生成可读的目录页。

### Modified Capabilities
（无）

## Impact

只动 `testenv/`、`reports/`、`openspec/`、`notes/`。基础世界的成本行与 `raw`（`ground_truth` 之外）逐字节不变，用 sha256 前后比对证明。AWS 只读：runbook 里的写操作命令只是给人看的文本，写明需人工审批和是否可逆，无任何执行路径。
