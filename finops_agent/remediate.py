"""Remediate: turn findings into reviewable dry-run plans.

A plan is DATA: command text, preconditions, reversal cost, rollback, owner and
evidence. Nothing here executes anything. This module deliberately imports no
process-spawning facility (tests assert it); `apply` can at most print or write
a script for a human to read and run.

Order follows docs/METHOD.md (delete -> downsize -> commit). Per FA06, actions
with a high reversal cost carry advice only; commitments get no commands at all.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field

# docs/METHOD.md order: delete, then downsize, then commit.
STEP_ORDER = {"M3_delete": 0, "M4_downsize_schedule": 1, "M5_commitment": 2}
REGION = '--region "$AWS_REGION"'
NO_OWNER = "unknown: findings carry no owner tag; ask the FinOps maintainer to resolve via CloudTrail/tags before notifying"


@dataclass
class Plan:
    plan_id: str
    finding_id: str
    type: str
    method_step: str
    order: int
    title: str
    resources: list
    monthly_savings_usd: float
    basis: str
    mode: str                  # commands | advice_only
    reversal_cost: str         # none | low | medium | high
    reversal_reason: str
    preconditions: list
    steps: list                # AWS CLI command text, never executed
    rollback: list
    owner: str
    evidence: list
    advice: str = ""
    executable: bool = False   # always False: only a human-run script can act

    def to_dict(self):
        return asdict(self)


def _ids(resources, prefix):
    return [r for r in resources if r.startswith(prefix)]


def _plan_unattached_volume(f):
    vol = f["resources"][0]
    return dict(
        mode="commands", reversal_cost="low",
        reversal_reason="删卷不可逆，但先打快照后可用快照重建卷；代价是快照存储费（远小于卷费用）",
        preconditions=[
            "确认该卷已连续 N 天（建议 >=14）处于 available，期间无挂载记录",
            "确认没有 ASG/启动模板/备份任务按卷 ID 引用它",
            "通知 owner 并获得回复或超过约定的等待期",
            "snapshot before delete：删卷前必须先打快照，且快照状态为 completed",
        ],
        steps=[
            f'SNAP_ID=$(aws ec2 create-snapshot --volume-id {vol} --description "pre-delete {f["id"]}" '
            f'--query SnapshotId --output text {REGION})',
            f'aws ec2 wait snapshot-completed --snapshot-ids "$SNAP_ID" {REGION}',
            f"aws ec2 delete-volume --volume-id {vol} {REGION}",
        ],
        rollback=[
            f'aws ec2 create-volume --snapshot-id "$SNAP_ID" --availability-zone <原可用区> {REGION}   # SNAP_ID 取自步骤 1',
            "把新卷挂回原实例，核对数据后再删除快照",
        ])


def _plan_idle_ip(f):
    alloc = f["resources"][0]
    return dict(
        mode="commands", reversal_cost="medium",
        reversal_reason="释放后该公网 IP 可能被他人领走，无法保证拿回；若对方白名单/DNS 引用了该 IP 会受影响",
        preconditions=[
            f"确认 {alloc} 当前没有 AssociationId（describe-addresses 复核）",
            "确认没有 DNS 记录、第三方白名单、防火墙规则引用该 IP",
            "记下 IP 地址，便于回滚时尝试原样领回",
        ],
        steps=[
            f"aws ec2 describe-addresses --allocation-ids {alloc} {REGION}",
            f"aws ec2 release-address --allocation-id {alloc} {REGION}",
        ],
        rollback=[f"aws ec2 allocate-address --address <原 IP> {REGION}   # 尽力而为，不保证成功",
                  "若失败，只能领新 IP 并更新所有引用方"])


def _plan_stopped_instance(f):
    inst = _ids(f["resources"], "i-")[0]
    return dict(
        mode="commands", reversal_cost="medium",
        reversal_reason="终止实例不可逆；先做 AMI（含全部卷快照）后可重建实例，但实例 ID、私网 IP、ENI 和实例存储会丢失",
        preconditions=[
            "确认实例停机原因（StateTransitionReason）和停机时长，已超过约定观察期",
            "确认该实例不是 ASG/启动模板的组成部分，且没有 DeleteOnTermination=false 之外的依赖",
            "owner tag 缺失，先找到 owner 并取得书面同意",
            "终止前必须先创建 AMI，且 AMI 状态为 available",
        ],
        steps=[
            f'AMI_ID=$(aws ec2 create-image --instance-id {inst} --name "pre-terminate-{inst}" '
            f'--no-reboot --query ImageId --output text {REGION})',
            f'aws ec2 wait image-available --image-ids "$AMI_ID" {REGION}',
            f"aws ec2 terminate-instances --instance-ids {inst} {REGION}",
        ],
        rollback=[f'aws ec2 run-instances --image-id "$AMI_ID" --instance-type <原机型> --subnet-id <原子网> {REGION}   # AMI_ID 取自步骤 1',
                  "重新绑定 tag、安全组与 IP，确认服务恢复后再清理 AMI 和快照"])


def _plan_orphan_snapshots(f):
    srcs = [r for r in f["resources"] if r.startswith(("vol-", "ami-"))]
    vols = _ids(srcs, "vol-")
    return dict(
        mode="commands", reversal_cost="high",
        reversal_reason="删快照/注销 AMI 不可逆，且没有任何手段在删除后恢复；本计划只给可逆的隔离步骤（打标），真正删除须在宽限期后另行评审",
        preconditions=[
            "逐个核对快照列表，确认不在任何 AMI、启动模板、备份策略中被引用",
            "保留集合（在用 AMI 的快照）必须从待处理列表中剔除",
            "owner 书面确认；法务/合规保留要求已排除",
            "宽限期（建议 >=30 天）内无人认领，才可再开一个审批做删除",
        ],
        steps=[
            *[f"aws ec2 describe-snapshots --owner-ids self --filters Name=volume-id,Values={v} {REGION}" for v in vols],
            "# 对上一步确认过的每个快照 ID 打隔离标签（可逆，不删除任何东西）：",
            f'aws ec2 create-tags --resources <snapshot-id> --tags Key=finops-pending-delete,Value={f["id"]} {REGION}',
        ],
        rollback=["aws ec2 delete-tags --resources <snapshot-id> --tags Key=finops-pending-delete " + REGION,
                  "隔离阶段不改变任何数据，回滚即去掉标签"],
        advice="删除本身（delete-snapshot / deregister-image）故意不在本计划内：宽限期后重新评审，并走单独的审批。")


def _plan_gp3(f):
    vol = f["resources"][0]
    return dict(
        mode="commands", reversal_cost="low",
        reversal_reason="modify-volume 在线完成、不中断；可改回 gp2，但同一卷两次修改之间需间隔 6 小时",
        preconditions=[
            f"确认 {vol} 近期 IOPS/吞吐峰值低于 gp3 基线（3000 IOPS / 125 MB/s），否则需显式配置 --iops/--throughput",
            "选择低峰时段；修改期间性能可能短暂受影响",
            "owner 知悉",
        ],
        steps=[f"aws ec2 describe-volumes --volume-ids {vol} {REGION}",
               f"aws ec2 modify-volume --volume-id {vol} --volume-type gp3 {REGION}",
               f"aws ec2 describe-volumes-modifications --volume-ids {vol} {REGION}"],
        rollback=[f"aws ec2 modify-volume --volume-id {vol} --volume-type gp2 {REGION}   # 距上次修改须 >=6 小时"])


def _plan_commitment(f):
    return dict(
        mode="advice_only", reversal_cost="high",
        reversal_reason="Savings Plan/RI 一旦购买不可取消、不可退款，期限 1-3 年；FA06：高撤回成本动作只给建议、不给执行路径",
        preconditions=["先完成删、降配两步，再按稳定基线评估", "先看现有承诺的利用率与覆盖率，利用率低时不买新的"],
        steps=[], rollback=[],
        advice="不要再购买承诺。现有计划利用率偏低（见证据）：先核对其覆盖的机型族是否已迁移，再决定是否在到期前调整用量；任何购买/修改由人在 Cost Explorer 控制台决定。")


HANDLERS = {
    "unattached_volume": _plan_unattached_volume,
    "idle_public_ip": _plan_idle_ip,
    "stopped_instance_storage": _plan_stopped_instance,
    "orphan_snapshots": _plan_orphan_snapshots,
    "gp2_to_gp3": _plan_gp3,
    "savings_plan_underutilized": _plan_commitment,
}


def build_plans(findings_doc, owners=None):
    """Return (plans, skipped). Pure function; no I/O."""
    owners = owners or {}
    plans, skipped = [], []
    for f in findings_doc["findings"]:
        h = HANDLERS.get(f["type"])
        wanted = f["monthly_savings_usd"] > 0 or f["method_step"] == "M5_commitment"
        if not wanted:
            continue
        if h is None:
            skipped.append({"finding_id": f["id"], "type": f["type"], "reason": "no remediation handler"})
            continue
        body = h(f)
        owner = next((owners[r] for r in f["resources"] if r in owners), NO_OWNER)
        plans.append(Plan(
            plan_id=f"P-{f['id']}", finding_id=f["id"], type=f["type"], method_step=f["method_step"],
            order=STEP_ORDER.get(f["method_step"], 9), title=f["title"], resources=f["resources"],
            monthly_savings_usd=round(f["monthly_savings_usd"], 2), basis=f["basis"],
            owner=owner, evidence=f["evidence"], **body))
    plans.sort(key=lambda p: (p.order, -p.monthly_savings_usd, p.plan_id))
    return plans, skipped


def render_script(plan):
    """Human-run script text for one plan. Writing it is the maximum this tool does."""
    if plan["mode"] != "commands" or not plan["steps"]:
        raise ValueError(f"{plan['plan_id']} is advice-only (reversal cost {plan['reversal_cost']}); there are no commands to emit")
    lines = ["#!/usr/bin/env bash",
             f"# {plan['plan_id']}  {plan['title']}",
             f"# reversal cost: {plan['reversal_cost']} - {plan['reversal_reason']}",
             f"# owner to notify: {plan['owner']}",
             "# GENERATED FOR HUMAN REVIEW. Not executed by finops-agent. Read every line, then run it yourself.",
             "", "# Preconditions (confirm each before running):"]
    lines += [f"#   [ ] {p}" for p in plan["preconditions"]]
    lines += ["", "set -euo pipefail", ': "${AWS_REGION:?set AWS_REGION first}"', ""]
    lines += plan["steps"]
    lines += ["", "# Rollback (manual):"] + [f"#   {r}" for r in plan["rollback"]]
    return "\n".join(lines) + "\n"


def cmd_plans(a):
    doc = json.load(open(a.findings))
    owners = json.load(open(a.owners)) if a.owners else None
    plans, skipped = build_plans(doc, owners)
    out = {"run_id": doc.get("run_id"), "dry_run": True, "order": "delete -> downsize -> commit",
           "plans": [p.to_dict() for p in plans], "skipped": skipped}
    with open(a.out, "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(f"{len(plans)} plans -> {a.out} (dry-run; nothing executed)")
    for p in plans:
        print(f"  {p.plan_id} [{p.mode}] reversal={p.reversal_cost} ${p.monthly_savings_usd:,.2f}/mo  {p.type}")
    return 0


def cmd_apply(a):
    if not a.approve:
        print("refused: apply needs --approve <plan_id>. This tool never executes anything; "
              "with approval it only prints a script for a human to run.", file=sys.stderr)
        return 2
    doc = json.load(open(a.plans))
    by_id = {p["plan_id"]: p for p in doc["plans"]}
    unknown = [i for i in a.approve if i not in by_id]
    if unknown:
        print(f"refused: unknown plan id(s): {unknown}", file=sys.stderr)
        return 2
    try:
        text = "\n".join(render_script(by_id[i]) for i in sorted(a.approve, key=lambda i: by_id[i]["order"]))
    except ValueError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    if a.script:
        with open(a.script, "w") as fh:   # plain file, no exec bit
            fh.write(text)
        print(f"script written to {a.script} (not executed; review and run it yourself)")
    else:
        print(text, end="")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="finops_agent.remediate", description="dry-run remediation plans (read-only tool)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plans", help="findings.json -> plans.json")
    p.add_argument("findings")
    p.add_argument("--out", required=True)
    p.add_argument("--owners", help="optional JSON {resource_id: owner}")
    p.set_defaults(fn=cmd_plans)
    q = sub.add_parser("apply", help="print (or write) a human-run script for approved plans; never executes")
    q.add_argument("plans")
    q.add_argument("--approve", action="append", metavar="PLAN_ID")
    q.add_argument("--script", help="write the script to this file instead of stdout")
    q.set_defaults(fn=cmd_apply)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
