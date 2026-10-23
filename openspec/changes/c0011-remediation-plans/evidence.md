# c0011 验收证据

## 3.1 D4 单测
```
test_apply_prints_script_only ... ok
test_apply_refuses_without_approve ... ok
test_apply_unknown_and_advice_only_refused ... ok
test_plans_writes_file ... ok
test_commands_are_plain_text ... ok
test_remediate_has_no_exec_capability ... ok
test_commitment_is_advice_only ... ok
test_destructive_steps_preceded_by_backup ... ok
test_every_saving_finding_has_plan ... ok
test_irreversible_snapshot_deletion_not_in_commands ... ok
test_order_delete_downsize_commit ... ok
test_owner_map ... ok
test_plan_fields_complete ... ok
Ran 13 tests in 0.014s
OK
```

## 3.2 make test / make check
```
Ran 3 tests in 0.063s
OK
Ran 7 tests in 1.060s
OK
Ran 32 tests in 1.994s
OK
check_rules: OK
```

## 3.3 CLI（plans / apply 拒绝 / apply 批准）
```
6 plans -> /tmp/p.json (dry-run; nothing executed)
  P-F04 [commands] reversal=medium $900.00/mo  stopped_instance_storage
  P-F05 [commands] reversal=high $190.00/mo  orphan_snapshots
  P-F02 [commands] reversal=low $50.00/mo  unattached_volume
  P-F03 [commands] reversal=medium $3.60/mo  idle_public_ip
  P-F06 [commands] reversal=low $20.00/mo  gp2_to_gp3
  P-F07 [advice_only] reversal=high $0.00/mo  savings_plan_underutilized
$ apply plans.json   (no --approve)
rc=2
$ apply plans.json --approve P-F07
rc=2
$ apply plans.json --approve P-F06
#!/usr/bin/env bash
# P-F06  1000 GB gp2 卷 vol-0db0000000000a001 可以换成 gp3
# reversal cost: low - modify-volume 在线完成、不中断；可改回 gp2，但同一卷两次修改之间需间隔 6 小时
# owner to notify: unknown: findings carry no owner tag; ask the FinOps maintainer to resolve via CloudTrail/tags before notifying
# GENERATED FOR HUMAN REVIEW. Not executed by finops-agent. Read every line, then run it yourself.

# Preconditions (confirm each before running):
#   [ ] 确认 vol-0db0000000000a001 近期 IOPS/吞吐峰值低于 gp3 基线（3000 IOPS / 125 MB/s），否则需显式配置 --iops/--throughput
#   [ ] 选择低峰时段；修改期间性能可能短暂受影响
#   [ ] owner 知悉

set -euo pipefail
: "${AWS_REGION:?set AWS_REGION first}"

aws ec2 describe-volumes --volume-ids vol-0db0000000000a001 --region "$AWS_REGION"
aws ec2 modify-volume --volume-id vol-0db0000000000a001 --volume-type gp3 --region "$AWS_REGION"
aws ec2 describe-volumes-modifications --volume-ids vol-0db0000000000a001 --region "$AWS_REGION"

# Rollback (manual):
#   aws ec2 modify-volume --volume-id vol-0db0000000000a001 --volume-type gp2 --region "$AWS_REGION"   # 距上次修改须 >=6 小时
```

## 3.4 openspec validate
```
Change 'c0011-remediation-plans' is valid
```

## 说明
- fixture 来自 `python3 -m finops_agent run ... --run-id t4 --no-state`（测试服务器 17566/17990）的真实输出，资源 ID 均为合成账号。
- 未改 README/__main__/报告/Makefile（集成留给后续 wave），所以没有 docs 阶段。
- findings 不带 owner，计划里 owner 默认标"未知，需先查"，可用 `--owners` 传入映射。
