# c0016 验收证据

命令输出原样粘贴；路径用仓库相对路径。

## 1. make eval（replay，端口 32566/32990）
```
python3 -m testenv.aws_server --port 32566 & echo $! > .aws_server.pid
python3 -m testenv.metrics_server --port 32990 & echo $! > .metrics_server.pid
test-aws-server listening on http://127.0.0.1:32566
test-metrics-server listening on http://127.0.0.1:32990
python3 -m finops_agent run --aws-endpoint http://127.0.0.1:32566 --prom http://127.0.0.1:32990 --run-id t7 --no-state
run t7: 12 findings, 7 leads, invariants pass
python3 -m eval.score runs/t7/findings.json; status=$?; /Applications/Xcode.app/Contents/Developer/usr/bin/make stop; exit $status
{"recall": 1.0, "savings_recall": 1.0, "precision": 1.0, "savings_accuracy": 0.9167, "step_agreement": 1.0, "depth": {"shallow_recall": 1.0, "deep_recall": 1.0}, "leads": 7}
missed: 
gates: pass
```

## 2. LLM 调用全部 replay
```
llm calls: 7 modes: ['replay']
judge prompts untouched: Lead / judge/ not modified; git diff d6024ba -- finops_agent/judge finops_agent/llm.py finops_agent/remediate.py eval testenv is empty (see section 6)
```

## 3. plans.json 检查：每个节省大于 0 的 finding 有带 reversal_cost 与 rollback 的计划
```
dry_run: True executed: False skipped: [] plans: 10 findings: 12
F01 misattributed_tags           savings=    0.00 owner=team-web  plan=-       reversal=-      rollback_steps=- OK
F02 unattached_volume            savings=   50.00 owner=未知        plan=P-F02   reversal=low    rollback_steps=2 OK
F03 idle_public_ip               savings=    3.60 owner=未知        plan=P-F03   reversal=medium rollback_steps=2 OK
F04 stopped_instance_storage     savings=  900.00 owner=未知        plan=P-F04   reversal=medium rollback_steps=2 OK
F05 orphan_snapshots             savings=  190.00 owner=未知        plan=P-F05   reversal=high   rollback_steps=2 OK
F06 gp2_to_gp3                   savings=   20.00 owner=team-api  plan=P-F06   reversal=low    rollback_steps=1 OK
F07 savings_plan_underutilized   savings=    0.00 owner=未知        plan=P-F07   reversal=high   rollback_steps=0 OK
F08 nat_path_cost                savings= 2332.80 owner=未知        plan=P-F08   reversal=low    rollback_steps=2 OK
F09 cross_az_traffic             savings=  759.85 owner=team-api  plan=P-F09   reversal=medium rollback_steps=1 OK
F10 busy_but_useless             savings= 1468.80 owner=team-data plan=P-F10   reversal=low    rollback_steps=1 OK
F11 always_on_batch              savings=  224.40 owner=team-web  plan=P-F11   reversal=low    rollback_steps=1 OK
F12 schedulable_idle             savings=    0.00 owner=team-web  plan=-       reversal=-      rollback_steps=- OK
violations: 0
```

## 4. 五段式（runs/t7/fivepart.json 摘录：F02 与 F10 完整五段）
```
--- F02 unattached_volume owner=未知 plan=P-F02
[status] 500 GB gp2 卷 vol-0orph00000000c001 未挂载；state=available, created 2026-04-02 08:00:00+00:00；$50.00/period。owner：未知。
[spec] available 的卷存在时间 ≤ 14 天，否则要有 owner 说明。
[diff] 存在 182 天，超出上限 14 天 168 天；可省 $50.00/月（口径 billed_14d_extrapolated）。
[runbook]
  - 验证：确认该卷已连续 N 天（建议 >=14）处于 available，期间无挂载记录
  - 验证：确认没有 ASG/启动模板/备份任务按卷 ID 引用它
  - 验证：通知 owner 并获得回复或超过约定的等待期
  - 验证：snapshot before delete：删卷前必须先打快照，且快照状态为 completed
  - 处置：`SNAP_ID=$(aws ec2 create-snapshot --volume-id vol-0orph00000000c001 --description "pre-delete F02" --query SnapshotId --output text --region "$AWS_REGION")`
  - 处置：`aws ec2 wait snapshot-completed --snapshot-ids "$SNAP_ID" --region "$AWS_REGION"`
  - 处置：`aws ec2 delete-volume --volume-id vol-0orph00000000c001 --region "$AWS_REGION"`
  - 回滚：aws ec2 create-volume --snapshot-id "$SNAP_ID" --availability-zone <原可用区> --region "$AWS_REGION"   # SNAP_ID 取自步骤 1；把新卷挂回原实例，核对数据后再删除快照
  - 审批：[需人工审批] 撤回成本 low：删卷不可逆，但先打快照后可用快照重建卷；代价是快照存储费（远小于卷费用）；通知 未知（先用 CloudTrail 与 tag 找到 owner 再通知）；agent 没有执行任何命令。
  - 确认：下次巡检 unattached_volume 变 resolved。
[prevention]
   控制：启动模板 / Terraform 里卷设 DeleteOnTermination=true，迁移任务的临时卷同样
   控制：tag policy 要求 owner 与 expire-on；SCP 拒绝创建缺这两个 tag 的卷
   控制：AWS Config 规则 ec2-volume-inuse-check 标记长期 available 的卷
   告警：alert:FinOpsSLOViolated
   节奏：每周看 orphan_max_age_days（docs/FINOPS_SLO.md Cadence 每周）
--- F10 busy_but_useless owner=team-data plan=P-F10
[status] fleet 计算花费（amortized，近 14 天折合月化）$1,468.80，每台 $244.80；fleet CPU（整个周期，各台取平均）：平均 58.7%，p95 63.8%，最大 64.0%，最小 28.0%；ingest_downstream_errors_total{reason=QueueDoesNotExist} 每天：周期前 3 天 0，最近 7 天 25,896；ingest_job_retries_total{-} 每天：周期前 3 天 43，最近 7 天 21,587；ingest_jobs_total{status=failed} 每天：周期前 3 天 9，最近 7 天 4,318。owner：team-data。
[spec] 消费链路健康：成功任务数与尝试数同量级，useful_work_ratio ≥ 95%。
[diff] ingest_jobs_total 成功占比（周期前 3 天）：99.8%（4,319 / 4,327 每天）；ingest_jobs_total 成功占比（最近 7 天）：0.0%（0 / 4,318 每天）；节省 1,468.80 取自候选 fleet_compute_monthly：整个 fleet 的计算花费月化；只在这些实例确实没做有用的事时才算浪费。fleet 的计算费全花在失败任务上，可省 $1,469/月（口径 billed_14d_extrapolated）。
[runbook]
  - 验证：先由 owner 确认失败根因（例如下游队列被删），并优先修根因；缩容只是止血
  - 验证：记下 ingest-asg 当前 MinSize / DesiredCapacity，回滚要用
  - 验证：确认 owner 同意暂停该 fleet 的全部作业
  - 处置：`aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names ingest-asg --region "$AWS_REGION"`
  - 处置：`aws autoscaling update-auto-scaling-group --auto-scaling-group-name ingest-asg --min-size 0 --desired-capacity 0 --region "$AWS_REGION"`
  - 回滚：aws autoscaling update-auto-scaling-group --auto-scaling-group-name ingest-asg --min-size <原 MinSize> --desired-capacity <原 DesiredCapacity> --region "$AWS_REGION"
  - 审批：[需人工审批] 撤回成本 low：把期望容量调到 0 只停实例，不删 ASG 与模板；改回原容量即恢复。但停掉期间该 fleet 的所有工作都会暂停；通知 team-data；agent 没有执行任何命令。
  - 确认：下次巡检 busy_but_useless 变 resolved。
[prevention]
   控制：删除队列前必须先查消费者，写进变更评审清单
   控制：任务成功率进 SLO（useful_work_ratio），重试上限与退避写进 worker 的 Terraform / 模板配置
   告警：alert:BusyButUselessFleet、alert:RetryStorm
   节奏：每日巡检看 useful_work_ratio（docs/FINOPS_SLO.md Cadence 每日）
```

## 5. make rot-demo
```
# no judge: the later-month worlds have no LLM cassettes (recording is a separate, deliberate act); rot is decided by deterministic detectors
FINOPS_NO_JUDGE=1 bash scripts/rot_demo.sh
== rot-1 (run 1, base world, period 2026-09) ==
   new=7  persisting=0  resolved=0  regressed=0
   new        misattributed_tags|i-0a1b2c3d4e5f60501
   new        unattached_volume|vol-0orph00000000c001
   new        idle_public_ip|eipalloc-0aa0000000000001
   new        stopped_instance_storage|i-0a1b2c3d4e5f60801,vol-0leg000000000b001
   new        orphan_snapshots|ami-ingest-v1,ami-ingest-v2,ami-ingest-v3,ami-ingest-v4,ami-ingest-v5,vol-0gone00000000d001
   new        gp2_to_gp3|vol-0db0000000000a001
   new        savings_plan_underutilized|sp-ec2-m5-01
== rot-2 (run 2, next_month, period 2026-10) ==
   new=1  persisting=4  resolved=3  regressed=0
   resolved   unattached_volume|vol-0orph00000000c001
   resolved   gp2_to_gp3|vol-0db0000000000a001
   resolved   idle_public_ip|eipalloc-0aa0000000000001
   new        unattached_volume|vol-0new000000000e001
== rot-3 (run 3, month_after, period 2026-11) ==
   new=1  persisting=4  resolved=1  regressed=1
   resolved   unattached_volume|vol-0new000000000e001
   regressed  gp2_to_gp3|vol-0db0000000000a001  (resolved in rot-2)
   new        idle_public_ip|eipalloc-0aa0000000000003
```

## 6. make test，以及未触碰的禁区
```
Ran 3 tests in 0.065s
OK
Ran 14 tests in 1.637s
OK
Ran 108 tests in 7.428s
OK
0 lines of diff --stat in forbidden paths (expect 0)
```
