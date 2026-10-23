# c0007 验收证据

## 5.1 make test / check / alerts-test
```
Ran 3 tests in 0.068s
OK
Ran 7 tests in 1.378s
OK
Ran 32 tests in 2.019s
OK
check_rules: OK
  SUCCESS: 11 rules found
  SUCCESS
```

## 5.2 两次运行：rot 检测与导出
```
run c0007-run1: 7 findings, 4 leads, invariants pass
run c0007-run2: 7 findings, 4 leads, invariants pass
c0007-run1 {'new': 7, 'persisting': 0, 'resolved': 0, 'regressed': 0}
c0007-run2 {'new': 0, 'persisting': 7, 'resolved': 0, 'regressed': 0}
promtool check metrics exit=0
```

## SLI 表（run1）

| SLI | 值 | 目标 | 状态 | 证据 |
|---|---|---|---|---|
| waste_ratio | 13.1% | <= 5% | violated | $1,143.60 billed-basis savings open / $8,712.90 spend；预算用掉 263%（预算 $436） |
| attribution_coverage | 25.4% | >= 90% | violated | $6,496.10 of $8,712.90 has no owner tag |
| commitment_utilization | 60.5% | >= 90% | violated | 60.48% in 2026-09, $682.91 unused |
| orphan_max_age_days | 182 days | <= 14 days | violated | oldest orphan vol-0orph00000000c001, 182 days |
| anomaly_time_to_detect_days | 27 days | <= 1 days | violated | NatGateway-Bytes rose 5.5x, starting 2026-09-04; first reported by this run, 27 days later |
| useful_work_ratio | 0.0% | >= 95% | violated | worst fleet ingest-worker: 0.0% of jobs succeeded in the last day |
| visibility_coverage | 50.0% | >= 100% | violated | useful_work_ratio=partial, rightsizing_headroom=missing, unit_cost_per_job=missing, cross_az_attribution=partial |
| remediation_age_days | — | <= 30 days | no_data |  |

## 5.3 eval 不回退
```
{"recall": 0.5833, "savings_recall": 0.1888, "precision": 1.0, "savings_accuracy": 1.0, "step_agreement": 1.0, "depth": {"shallow_recall": 1.0, "deep_recall": 0.4444}, "leads": 4}
gates: pass
```

## 5.4 openspec validate
```
Change 'c0007-finops-slo' is valid
```

## 顺带发现

- promtool 单测抓到我写的测试数据问题：小时级样本超过 Prometheus 5 分钟回看窗口，for: 1d 的计时在样本之间被重置。真实导出器按分钟级被抓取，测试改成 1 分钟样本。
- 文档里先写了快烧/慢烧告警，代码里还没有；为了不让文档领先于实现，补了 finops_waste_usd / finops_waste_budget_usd 两个导出和两条规则，并加了 promtool 测试。
- check_rules 拦下了对 runs/state.json 的引用：它是运行时生成、不进 git 的文件，新 clone 里不存在。
- 验收时发现 SLI 表把「≤ 1 天」显示成「≤ 100%」：报告用 target ≤ 1 猜单位。改为在 finops_slo.yaml 显式声明 unit（ratio / days），报告与证据表都按 unit 格式化。
