# c0023 evidence

## E1 基础世界线索与 cassette 键前后逐字节相同（before = main，after = 本分支）

```
base leads identical: True | count 7 7
base cassette keys identical: True | count 7
base leads json sha256 before/after: 776bb1a9ba3b26ac 776bb1a9ba3b26ac
```

## E2 样本外 replay（python3 -m eval.heldout）

```
run base: 12 findings, 7 leads, invariants pass
run next_month: 10 findings, 7 leads, invariants pass
run month_after: 11 findings, 7 leads, invariants pass
| world | kind | recall | savings_recall | precision | savings_accuracy | savings_accuracy_day_scaled | step_agreement | traps | invariants | findings/GT | LLM calls | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base (in-sample) | in-sample | 1.0 | 1.0 | 1.0 | 0.9167 | 0.9167 | 1.0 | 0 | 0 | 12/12 | 7 | $0.1426 |
| next_month | held-out | 1.0 | 1.0 | 1.0 | 0.8 | 1.0 | 1.0 | 0 | 0 | 10/10 | 7 | $0.1839 |
| month_after | held-out | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0 | 0 | 11/11 | 7 | $0.1617 |

[base (in-sample)] missed: none; depth={'shallow_recall': 1.0, 'deep_recall': 1.0}
[base (in-sample)] judged: L01:cost_growth=waste; L02:unattributed_transfer=waste; L03:fleet_work=not_waste; L04:fleet_work=waste; L05:idle_window=waste; L06:idle_window=waste; L07:idle_window=not_waste
[base (in-sample)] missed savings share: {}; savings outside the GT range: [{'gt': 'GT02', 'finding': 'F08', 'savings': 2332.8, 'range': {'min': 2400, 'max': 2900}}]
```

## E3 新线索（next_month）与取证器选择

```
run x: 10 findings, 7 leads, invariants pass
L04 NatGateway-Bytes 比此前基线高 5.5 倍，周期开始前就已抬高（自 2026-09-04 起） since 2026-09-04
NatGateway-Bytes：本周期日均中位 $95.11/天，此前 92 天基线（P25）$17.35/天
F08 2948.47 NatGateway-Bytes 当前月化 $2,948.47，其中比基线多出的部分 $-0.00（(最近 7 天均值 - 前 3 天均值) x 31 天）
```

## E4 单测

```
test_an_in_window_jump_keeps_its_single_lead (finops_agent.test_analyze.PersistentAnomalyTest.test_an_in_window_jump_keeps_its_single_lead) ... ok
test_elevated_from_before_the_window_gets_a_lead_with_the_true_onset (finops_agent.test_analyze.PersistentAnomalyTest.test_elevated_from_before_the_window_gets_a_lead_with_the_true_onset) ... ok
test_flat_cost_gets_no_lead (finops_agent.test_analyze.PersistentAnomalyTest.test_flat_cost_gets_no_lead) ... ok
test_no_history_means_no_baseline_and_no_lead (finops_agent.test_analyze.PersistentAnomalyTest.test_no_history_means_no_baseline_and_no_lead) ... ok
test_small_spend_is_ignored (finops_agent.test_analyze.PersistentAnomalyTest.test_small_spend_is_ignored) ... ok
test_usage_new_in_the_window_is_not_a_persistent_anomaly (finops_agent.test_analyze.PersistentAnomalyTest.test_usage_new_in_the_window_is_not_a_persistent_anomaly) ... ok
test_lifecycle_new_persist_resolve_regress (finops_agent.test_slo.DiffStateTest.test_lifecycle_new_persist_resolve_regress) ... ok
test_same_resource_different_type_is_a_different_finding (finops_agent.test_slo.DiffStateTest.test_same_resource_different_type_is_a_different_finding) ... ok
test_prometheus_export (finops_agent.test_slo.EvaluateTest.test_prometheus_export) ... ok
test_status_and_budget (finops_agent.test_slo.EvaluateTest.test_status_and_budget) ... ok
test_cost_line_dropped_is_resolved (finops_agent.test_slo.NotRedetectedTest.test_cost_line_dropped_is_resolved) ... ok
test_not_redetected_persists_then_resolves_then_regresses (finops_agent.test_slo.NotRedetectedTest.test_not_redetected_persists_then_resolves_then_regresses) ... ok
test_prometheus_state_label_includes_not_redetected (finops_agent.test_slo.NotRedetectedTest.test_prometheus_state_label_includes_not_redetected) ... ok
test_redetected_after_a_miss_is_persisting (finops_agent.test_slo.NotRedetectedTest.test_redetected_after_a_miss_is_persisting) ... ok
test_resource_absent_is_resolved (finops_agent.test_slo.NotRedetectedTest.test_resource_absent_is_resolved) ... ok
test_resource_still_there_and_unchanged_is_not_redetected_not_resolved (finops_agent.test_slo.NotRedetectedTest.test_resource_still_there_and_unchanged_is_not_redetected_not_resolved) ... ok
test_type_changed_in_place_is_resolved (finops_agent.test_slo.NotRedetectedTest.test_type_changed_in_place_is_resolved) ... ok
test_without_a_snapshot_the_old_behavior_holds (finops_agent.test_slo.NotRedetectedTest.test_without_a_snapshot_the_old_behavior_holds) ... ok
test_month_after_restores_the_regressed_volume_and_adds_the_leaked_ip (eval.test_heldout.ExpectedGroundTruthTest.test_month_after_restores_the_regressed_volume_and_adds_the_leaked_ip) ... ok
test_next_month_drops_three_resolved_and_adds_the_new_volume (eval.test_heldout.ExpectedGroundTruthTest.test_next_month_drops_three_resolved_and_adds_the_new_volume) ... ok
test_traps_are_unchanged (eval.test_heldout.ExpectedGroundTruthTest.test_traps_are_unchanged) ... ok
test_gates_pass_on_held_out_worlds (eval.test_heldout.HeldoutReplayTest.test_gates_pass_on_held_out_worlds) ... ok
test_held_out_metrics_are_reported_separately_and_pinned (eval.test_heldout.HeldoutReplayTest.test_held_out_metrics_are_reported_separately_and_pinned) ... ok
Not evidence of generalization: c0023 targeted exactly the GT02 miss seen here. A fresh world is needed. ... ok
test_in_sample_equals_the_baseline (eval.test_heldout.HeldoutReplayTest.test_in_sample_equals_the_baseline) ... ok
test_no_trap_or_invariant_violations_and_every_judgment_accepted (eval.test_heldout.HeldoutReplayTest.test_no_trap_or_invariant_violations_and_every_judgment_accepted) ... ok
Ran 26 tests in 3.282s
OK
```

## E5 rot 链路（scripts/rot_demo.sh，端口 16566/16990 空闲）

```
== rot-1 (run 1, base world, period 2026-09) ==
   new=12  persisting=0  resolved=0  regressed=0  not_redetected=0
== rot-2 (run 2, next_month, period 2026-10) ==
   new=1  persisting=9  resolved=3  regressed=0  not_redetected=0
   resolved   gp2_to_gp3|vol-0db0000000000a001
   resolved   idle_public_ip|eipalloc-0aa0000000000001
   resolved   unattached_volume|vol-0orph00000000c001
== rot-3 (run 3, month_after, period 2026-11) ==
   new=1  persisting=9  resolved=1  regressed=1  not_redetected=0
   resolved   unattached_volume|vol-0new000000000e001
   regressed  gp2_to_gp3|vol-0db0000000000a001  (resolved in rot-2)
```

## E6 漏检不再记成 resolved：第 1 次带 judge，第 2 次（同 10 月世界）关 judge，判断层的 finding 都没再检出但资源还在

```
run r1: 12 findings, 7 leads, invariants pass
run r2: 5 findings, 4 leads, invariants pass
resolved 3
not_redetected 5
new 1
persisting 4
regressed 0
  resolved gp2_to_gp3|vol-0db0000000000a001
  resolved idle_public_ip|eipalloc-0aa0000000000001
  resolved unattached_volume|vol-0orph00000000c001
  not_redetected always_on_batch|i-0a1b2c3d4e5f60501 | i-0a1b2c3d4e5f60501 仍在清单里，属性和成本与检测时一致
  not_redetected busy_but_useless|i-0a1b2c3d4e5f60401,i-0a1b2c3d4e5 | i-0a1b2c3d4e5f60401,i-0a1b2c3d4e5f60402,i-0a1b2c3d4e5f60403,
  not_redetected cross_az_traffic|i-0a1b2c3d4e5f60201,i-0a1b2c3d4e5 | i-0a1b2c3d4e5f60201,i-0a1b2c3d4e5f60202,i-0a1b2c3d4e5f60203,
  not_redetected nat_path_cost|nat-0a11c0ffee0000001 | nat-0a11c0ffee0000001 仍在清单里，属性和成本与检测时一致
  not_redetected schedulable_idle|i-0a1b2c3d4e5f60601,i-0a1b2c3d4e5 | i-0a1b2c3d4e5f60601,i-0a1b2c3d4e5f60602,i-0a1b2c3d4e5f60603 
```

## E7 make eval（基础指标不变）

```
run t20: 12 findings, 7 leads, invariants pass
{"recall": 1.0, "savings_recall": 1.0, "precision": 1.0, "savings_accuracy": 0.9167, "step_agreement": 1.0, "depth": {"shallow_recall": 1.0, "deep_recall": 1.0}, "leads": 7}
missed: 
gates: pass
```

## E8 alert 规则：只读检查

```
config/alerts/finops.rules.test.yml:42:      - series: 'finops_findings{state="regressed"}'
config/alerts/finops.rules.yml:2:#   finops-slo      on the SLIs each agent run exports (finops_sli, finops_findings, ...)
config/alerts/finops.rules.yml:42:        expr: finops_findings{state="regressed"} > 0
```

## E9 make test / openspec validate

```
Ran 3 tests in 0.072s
OK
Ran 14 tests in 2.208s
OK
Ran 116 tests in 7.641s
OK
Change 'c0023-persistent-anomaly-and-resolution' is valid
```
