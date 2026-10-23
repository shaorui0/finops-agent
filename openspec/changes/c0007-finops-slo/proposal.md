## Why

一次清理之后系统会重新腐烂：新资源不打 tag、孤儿堆积、承诺漂移、运行时异常放大成本。要回答"这次做了，下次呢；什么时候又开始腐烂；FinOps 的 SLO 是什么"，就要把成本健康当成可靠性来管：SLI、SLO、浪费预算、告警、巡检节奏，以及跨运行的复发检测。

## What Changes

- `config/finops_slo.yaml` + `finops_agent/slo.py`：8 个 SLI（浪费比例、归因覆盖、承诺利用率、孤儿年龄、异常发现时延、有效工作比例、可见性覆盖、修复时长），浪费预算；跨运行状态 `runs/state.json`，finding 分为 new / persisting / resolved / regressed。
- 每次运行导出 `finops_metrics.prom`（Prometheus 文本格式，供 textfile collector / pushgateway）；报告新增 FinOps SLO 一节。
- `config/alerts/finops.rules.yml`：11 条规则，两组：SLO 层（SLO 违反、预算耗尽、快烧/慢烧、复发、巡检停摆）与信号层（busy-but-useless、重试风暴、NAT 激增、dev 空转、可见性指标消失）；`finops.rules.test.yml` 用 promtool 单测。
- `make inspect`（cron 调用）、`make alerts-test`；`ops/crontab.example`；CI 增加 alerts-test。
- `docs/FINOPS_SLO.md`：腐烂来源、SLI 取舍、浪费预算、复发、巡检节奏。

## Capabilities

### New Capabilities
- `finops-slo`：SLI 计算、SLO 判定、浪费预算、跨运行状态与导出。
- `finops-alerts`：告警规则及其单元测试。

### Modified Capabilities
（无）

## Impact

`python3 -m finops_agent run` 默认更新 `runs/state.json`（`--no-state` 关闭；`make demo/eval` 使用 `--no-state` 以保持评估可重复）。
