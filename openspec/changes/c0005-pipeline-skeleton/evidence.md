# c0005 验收证据

## 4.1 全链路测试
```
test_artifacts_written (finops_agent.test_pipeline.PipelineTest.test_artifacts_written) ... ok
test_every_finding_has_method_step_and_evidence (finops_agent.test_pipeline.PipelineTest.test_every_finding_has_method_step_and_evidence) ... ok
test_invariants_pass (finops_agent.test_pipeline.PipelineTest.test_invariants_pass) ... ok
test_leads_point_at_deep_findings (finops_agent.test_pipeline.PipelineTest.test_leads_point_at_deep_findings) ... ok
test_misattribution_found_despite_injection (finops_agent.test_pipeline.PipelineTest.test_misattribution_found_despite_injection) ... ok
test_trace_is_read_only (finops_agent.test_pipeline.PipelineTest.test_trace_is_read_only) ... ok
test_traps_not_flagged (finops_agent.test_pipeline.PipelineTest.test_traps_not_flagged) ... ok
test_two_hop_findings (finops_agent.test_pipeline.PipelineTest.test_two_hop_findings) ... ok
test_visibility_gaps_match_planted (finops_agent.test_pipeline.PipelineTest.test_visibility_gaps_match_planted) ... ok
Ran 9 tests in 0.969s
OK
```

## 4.2 对着运行中的服务器跑
```
run acceptance: 7 findings, 4 leads, invariants pass
runs/acceptance/report.html
```

## 快照重放（不访问 AWS）
```
run replay: 7 findings, 4 leads, invariants pass
runs/replay/report.html
findings identical: True
aws calls in replay: 0
```

## 本次运行结果

| ID | 步骤 | 类型 | 节省 | 口径 |
|---|---|---|---|---|
| F01 | M1_visibility_attribution | misattributed_tags | $0.00 | none |
| F02 | M3_delete | unattached_volume | $50.00 | billed_14d_extrapolated |
| F03 | M3_delete | idle_public_ip | $3.60 | billed_14d_extrapolated |
| F04 | M3_delete | stopped_instance_storage | $900.00 | billed_14d_extrapolated |
| F05 | M3_delete | orphan_snapshots | $190.00 | billed_14d_extrapolated |
| F06 | M4_downsize_schedule | gp2_to_gp3 | $20.00 | list_price |
| F07 | M5_commitment | savings_plan_underutilized | $0.00 | none |

Leads：L01 NatGateway-Bytes rose 5.5x, starting 2026-09-04；L02 DataTransfer-Regional-Bytes costs $760 with no resource id；L03 web-asg: 4 instances; is the fleet doing useful work?；L04 ingest-asg: 6 instances; is the fleet doing useful work?

可见性第 ④ 环：idle_detection=covered；useful_work_ratio=partial；rightsizing_headroom=missing；latency_slo_guard=covered；schedule_detection=covered；unit_cost_per_job=missing；cross_az_attribution=partial；nat_attribution=covered

对照 ground truth（粗看，正式打分在 c0006）：确定性层命中 7/12：GT04, GT06, GT07, GT08, GT09, GT10, GT11；未命中的 GT01, GT02, GT03, GT05, GT12 需要判断层。

## 4.3 回归
```
OK
OK
OK
check_rules: OK
```

## 4.4 openspec validate
```
Change 'c0005-pipeline-skeleton' is valid
```
