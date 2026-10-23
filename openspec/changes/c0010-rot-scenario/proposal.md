## Why

腐化检测（`finops_agent/slo.py` 的 `diff_state`：new / persisting / resolved / regressed）只有单测覆盖，没有端到端演示：合成账号只有一个月，agent 跑两次得到的是同一份结果，`resolved` 和 `regressed` 永远是 0。没有"下个月"，就没法证明 rot 检测在真实流程里能工作。

## What Changes

- `testenv.aws_server` / `testenv.metrics_server` 增加 `--world <path>`，默认仍是 `testenv/world.yaml`。
- 世界文件支持两种形态：完整世界，或"覆盖层"（overlay，`scenario.base` 指向被修改的世界，按 set → remove → patch → add 应用）。
- 新增两个覆盖层：`testenv/scenarios/next_month.yaml`（2026-10）和 `month_after.yaml`（2026-11，叠在前者之上）。各自的期望 diff 写在文件里的 `scenario.expect`。
- `scripts/rot_demo.sh`：三次运行共用一个临时 state 文件，打印每次 diff。
- testenv 测试：`--world` 加载、覆盖层语义、场景自洽（真实跑 agent 三次，diff 与 `scenario.expect` 逐项相等）。

## Capabilities

### New Capabilities
- `rot-scenario`：合成账号的"下个月"场景与端到端腐化演示。

### Modified Capabilities
（无）

## Impact

只动 `testenv/`、`scripts/`。不带 `--world` 时世界、成本行、指标、ground_truth 与改动前逐字节一致（对 `raw` 和全部成本行取 sha256 比对）。不涉及 AWS 写操作。
