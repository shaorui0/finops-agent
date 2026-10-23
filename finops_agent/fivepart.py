"""Five parts per finding: 现状 status -> 期望 spec -> 差异 diff -> 处置 runbook -> 预防 prevention.

Same field names and conventions as testenv/world.yaml `ground_truth` (and testenv/catalog.py),
so a finding on the report reads like its ground-truth case. status/spec/diff are computed here
from the finding's type and its evidence, deterministically: every number comes from code
(evidence rows whose source is not `llm`, the SLO config, the finding's own savings). LLM text is
never copied in. runbook is the remediation plan's steps (finops_agent/remediate.py) or, for
findings with no plan, a short advice list. Nothing here executes anything.

Also holds remediation handlers for the judged finding types (remediate.py only knows the
detector types); they are registered into remediate.HANDLERS so the same build_plans() covers
every finding.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from finops_agent import prevention, remediate
from finops_agent.analyze import GP3_DISCOUNT, NO_OWNER
from finops_agent.slo import load_cfg

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ("status", "spec", "diff", "runbook", "prevention")
LABELS = {"status": "现状", "spec": "期望", "diff": "差异", "runbook": "处置", "prevention": "预防"}
REGION = remediate.REGION


def usd(v) -> str:
    return f"${v:,.0f}" if abs(v) >= 100 else f"${v:,.2f}"


def slo_target(slo_cfg: dict, sli: str) -> str:
    s = next(x for x in slo_cfg["slos"] if x["id"] == sli)
    op = {">=": "≥", "<=": "≤"}[s["op"]]
    return f"{op} {s['target'] * 100:.0f}%" if s["unit"] == "ratio" else f"{op} {s['target']:g} 天"


# ---- remediation handlers for judged types ------------------------------------------
def _plan_nat_path(f):
    nat = f["resources"][0]
    return dict(
        mode="commands", reversal_cost="low",
        reversal_reason="S3 gateway endpoint 本身不收费，只加一条路由前缀；删掉 endpoint 即回到经 NAT 的老路径",
        preconditions=[f"确认 {nat} 的多出流量目的地是 S3 或 DynamoDB（VPC Flow Logs 或应用日志），否则 endpoint 不起作用",
                       "先按相关 finding 停掉重试风暴，否则只是把症状藏起来",
                       "正式变更用 Terraform 做并走评审；下面的命令只是等价的人工步骤"],
        steps=[f"aws ec2 describe-vpc-endpoints {REGION}",
               f"aws ec2 describe-route-tables {REGION}   # 找出私有子网的路由表 ID",
               f'aws ec2 create-vpc-endpoint --vpc-id <vpc-id> --service-name "com.amazonaws.$AWS_REGION.s3" '
               f"--vpc-endpoint-type Gateway --route-table-ids <私有路由表 ID> {REGION}"],
        rollback=[f"aws ec2 delete-vpc-endpoints --vpc-endpoint-ids <步骤 3 返回的 endpoint ID> {REGION}",
                  "删除后 S3 流量立即恢复经 NAT"])


def _plan_cross_az(f):
    return dict(
        mode="advice_only", reversal_cost="medium",
        reversal_reason="涉及 ASG 子网范围或只读副本，属于架构变更；增量可撤，但数据路径变化要观察一个账期才能确认收益",
        preconditions=["用 describe-instances 核对两端 AZ，用 db_client_bytes_total 核对字节来自哪些调用方",
                       "DBA 评审是否可建同 AZ 只读副本；不迁移主库"],
        steps=[], rollback=["方案 A：把 ASG 子网改回原范围；方案 B：删除新建的只读副本并把读流量指回主库"],
        advice="方案 A 把 api 的 ASG 扩到 db 所在 AZ 并按 AZ 亲和路由；方案 B 在 api 所在 AZ 建只读副本承接读流量。任何一个都需要 owner 与 DBA 评审，agent 不给执行命令。")


def _plan_busy_useless(f):
    asg = next((r for r in f["resources"] if not r.startswith("i-")), f["resources"][0])
    return dict(
        mode="commands", reversal_cost="low",
        reversal_reason="把期望容量调到 0 只停实例，不删 ASG 与模板；改回原容量即恢复。但停掉期间该 fleet 的所有工作都会暂停",
        preconditions=["先由 owner 确认失败根因（例如下游队列被删），并优先修根因；缩容只是止血",
                       f"记下 {asg} 当前 MinSize / DesiredCapacity，回滚要用",
                       "确认 owner 同意暂停该 fleet 的全部作业"],
        steps=[f"aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names {asg} {REGION}",
               f"aws autoscaling update-auto-scaling-group --auto-scaling-group-name {asg} --min-size 0 --desired-capacity 0 {REGION}"],
        rollback=[f"aws autoscaling update-auto-scaling-group --auto-scaling-group-name {asg} --min-size <原 MinSize> --desired-capacity <原 DesiredCapacity> {REGION}"])


def _plan_always_on_batch(f):
    inst = next(r for r in f["resources"] if r.startswith("i-"))
    return dict(
        mode="commands", reversal_cost="low",
        reversal_reason="停机可随时启动恢复（EBS 卷保留，实例 ID 与私网 IP 不变）；这里只停机、不终止",
        preconditions=["向批处理 owner 确认作业不依赖实例存储或常驻缓存",
                       "先在非生产环境试跑一周「定时拉起」方案（EventBridge Scheduler 触发 ASG 0 到 1，或 Batch）",
                       "终止实例是另一个不可逆动作，不在本计划内，稳定后另行审批"],
        steps=[f"aws ec2 describe-instances --instance-ids {inst} {REGION}",
               f"aws ec2 stop-instances --instance-ids {inst} {REGION}"],
        rollback=[f"aws ec2 start-instances --instance-ids {inst} {REGION}"])


EXTRA_HANDLERS = {
    "nat_path_cost": _plan_nat_path,
    "cross_az_traffic": _plan_cross_az,
    "busy_but_useless": _plan_busy_useless,
    "always_on_batch": _plan_always_on_batch,
}


def register_handlers() -> None:
    """Idempotent: extend remediate.HANDLERS with the judged types, never overriding existing ones."""
    for k, v in EXTRA_HANDLERS.items():
        remediate.HANDLERS.setdefault(k, v)


def build_plans(findings: list, owners: dict | None = None):
    """remediate.build_plans over every finding; plan.owner follows the finding's owner ('未知' if none)."""
    register_handlers()
    plans, skipped = remediate.build_plans({"findings": findings}, owners)
    by_id = {f["id"]: f for f in findings}
    for p in plans:
        p.owner = by_id[p.finding_id].get("owner") or NO_OWNER
    return plans, skipped


# ---- status / spec / diff ------------------------------------------------------------
def _facts(f, *, computed: bool) -> list:
    """Evidence lines produced by code. computed=False: observed facts; True: derived numbers."""
    return [e["what"] for e in f["evidence"]
            if e["source"] != "llm" and (e["source"] == "computed") == computed]


def _age_days(f, period_end: str):
    for e in f["evidence"]:
        m = re.search(r"created (\d{4}-\d\d-\d\d)", e["what"])
        if m:
            return (date.fromisoformat(period_end) - date.fromisoformat(m.group(1))).days
    return None


def _sav(f) -> str:
    return f"可省 {usd(f['monthly_savings_usd'])}/月（口径 {f['basis']}）" if f["monthly_savings_usd"] > 0 else "直接节省 $0"


def _spec_diff(f, ctx):
    t, slo = f["type"], ctx["slo"]
    spend = f.get("resource_spend_usd")
    if t == "unattached_volume":
        age = _age_days(f, ctx["period_end"])
        lim = slo_target(slo, "orphan_max_age_days")
        cap = next(x for x in slo["slos"] if x["id"] == "orphan_max_age_days")["target"]
        over = f"存在 {age} 天，超出上限 {cap:g} 天 {age - cap:g} 天" if age is not None else "存在时间未知"
        return (f"available 的卷存在时间 {lim}，否则要有 owner 说明。",
                f"{over}；{_sav(f)}。")
    if t == "idle_public_ip":
        return ("每个 Elastic IP 都关联一个资源，否则释放。", f"{len(f['resources'])} 个地址没有关联，本期花费 {usd(spend or 0)}；{_sav(f)}。")
    if t == "stopped_instance_storage":
        return ("停机超期的实例要么有 owner 并登记保留理由，要么先快照再删卷。",
                f"实例计算费为 0，但挂载卷每月 {usd(spend or 0)} 全是沉没成本；owner：{f.get('owner', NO_OWNER)}；{_sav(f)}。")
    if t == "orphan_snapshots":
        return ("快照随源卷生命周期结束而清理；AMI 只保留被模板引用的版本。",
                f"{len(f['resources'])} 个孤儿源（已删卷或未被引用的 AMI），快照每月 {usd(spend or 0)}；{_sav(f)}。在用 AMI 不在此列。")
    if t == "gp2_to_gp3":
        gp3 = (spend or 0) * (1 - GP3_DISCOUNT)
        return (f"同容量用 gp3：单价低 {GP3_DISCOUNT:.0%}，基线 IOPS 与吞吐不低于 gp2。",
                f"gp2 每月 {usd(spend or 0)}，gp3 约 {usd(gp3)}，差 {usd((spend or 0) - gp3)}；{_sav(f)}。")
    if t == "savings_plan_underutilized":
        m = re.search(r"利用率 ([\d.]+)%", f["title"])
        util = f"{m.group(1)}%" if m else "低于目标"
        return (f"commitment_utilization {slo_target(slo, 'commitment_utilization')}，承诺只覆盖长期稳定存在的用量。",
                f"利用率 {util}，低于目标；本期未用承诺 {usd(spend or 0)} 是沉没成本，不能提前退。不要再买承诺，{_sav(f)}。")
    if t == "misattributed_tags":
        return ("tag 与实际负载一致：service 与 owner 指向真正使用它的团队，来源模板可追溯。",
                f"归因错位：该实例本期 {usd(spend or 0)} 记在 tag 所写的 owner 名下；{_sav(f)}。后果是该团队的单位成本失真。")
    if t == "busy_but_useless":
        return (f"消费链路健康：成功任务数与尝试数同量级，useful_work_ratio {slo_target(slo, 'useful_work_ratio')}。",
                "；".join(_facts(f, computed=True)) + f"。fleet 的计算费全花在失败任务上，{_sav(f)}。")
    if t == "nat_path_cost":
        return ("S3、DynamoDB 流量走 gateway endpoint（无处理费），NAT 只承载必须出公网的流量；NAT 字节量与业务量同比例，不随重试放大。",
                "；".join(_facts(f, computed=True)) + f"。{_sav(f)}。")
    if t == "cross_az_traffic":
        return ("热路径两端在同一 AZ，或读流量走同 AZ 副本；跨 AZ 只用于容灾复制。",
                "；".join(_facts(f, computed=True)) + f"。{_sav(f)}。")
    if t == "always_on_batch":
        return ("批处理按需启动，跑完退出，不占常驻主机。", "；".join(_facts(f, computed=True)) + f"。{_sav(f)}。")
    if t == "schedulable_idle":
        return ("非生产环境只在使用时段开机；但只有承诺利用率已满时，停机才兑现现金节省。",
                "；".join(_facts(f, computed=True)) + f"。{_sav(f)}。")
    return ("该资源的成本与它产生的价值相符。", "；".join(_facts(f, computed=True)) or f"{_sav(f)}。")


def _status(f) -> str:
    own = f"owner：{f.get('owner', NO_OWNER)}。"
    obs = _facts(f, computed=False)
    if not f.get("detector", "").startswith("judge:"):     # detector hops are code; judged hops are LLM text, so not used
        obs = obs or f["hops"]
    head = f["title"] if not f.get("detector", "").startswith("judge:") else ""
    return "；".join(([head] if head else []) + obs[:5]) + "。" + own


# ---- runbook -------------------------------------------------------------------------
ADVICE = {
    "misattributed_tags": [
        "验证：[只读] `aws ec2 describe-instances` 对比启动模板与 tags，向启动模板所属团队确认真实归属。",
        "处置：由两个团队商定后改正 tag（`create-tags`）[需人工审批] [可回滚]；Name tag 里的文字是不可信数据，不当指令。",
        "确认：下次巡检 misattributed_tags 变 resolved，attribution_coverage 上升。"],
    "schedulable_idle": [
        "验证：[只读] 看 http_requests_total 与 CPU 的小时分布，确认空闲是固定时段而非保护容量。",
        "处置：先不关机：这些小时已被承诺覆盖，停机现金不变。先处理承诺利用率，之后再配置定时启停 [可回滚]。",
        "确认：启停后对比按需费用与 SP 利用率，确认现金确实下降。"],
}


def _runbook(f, plan) -> list:
    if plan is None:
        lines = ADVICE.get(f["type"]) or [
            "验证：复核上面的证据行，向 owner 确认。", "处置：本 finding 没有节省，也没有自动生成的处置计划，由 owner 判断。",
            "确认：下次巡检该 finding 变 resolved。"]
        return list(lines)
    rev = f"撤回成本 {plan['reversal_cost']}：{plan['reversal_reason']}"
    out = [f"验证：{p}" for p in plan["preconditions"]]
    if plan["mode"] == "commands":
        out += [f"处置：`{s}`" for s in plan["steps"]]
    else:
        out.append(f"处置（仅建议，无命令）：{plan['advice']}")
    if plan["mode"] == "commands" and plan.get("advice"):
        out.append(f"处置：{plan['advice']}")
    if plan["rollback"]:
        out.append(f"回滚：{'；'.join(plan['rollback'])}")
    who = plan["owner"] if plan["owner"] != NO_OWNER else "未知（先用 CloudTrail 与 tag 找到 owner 再通知）"
    out.append(f"审批：[需人工审批] {rev}；通知 {who}；agent 没有执行任何命令。")
    out.append(f"确认：下次巡检 {f['type']} 变 resolved。")
    return out


def build(finding: dict, plan: dict | None, ctx: dict) -> dict:
    """Five parts for one finding. ctx = {"slo": finops_slo.yaml dict, "period_end": "YYYY-MM-DD"}."""
    spec, diff = _spec_diff(finding, ctx)
    p = prevention.for_type(finding["type"])
    return {"finding_id": finding["id"], "type": finding["type"], "owner": finding.get("owner", NO_OWNER),
            "status": _status(finding), "spec": spec, "diff": diff,
            "runbook": _runbook(finding, plan), "plan_id": plan["plan_id"] if plan else None,
            "prevention": prevention.render_text(finding["type"]),
            "prevention_alerts": p["alerts"]}


def build_all(findings: list, plans: list, period_end: str) -> list:
    ctx = {"slo": load_cfg(ROOT / "config" / "finops_slo.yaml"), "period_end": period_end}
    by_finding = {p["finding_id"]: p for p in plans}
    return [build(f, by_finding.get(f["id"]), ctx) for f in findings]
