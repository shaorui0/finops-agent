"""Evidence gatherers: one per lead kind. They query the snapshot and Prometheus and COMPUTE every
number the judge may rely on (costs, ratios, GB, candidate savings). The LLM never does arithmetic.

Also holds the deterministic generator for idle-window leads (instances busy for only part of the day
or week), which needs metrics and therefore cannot live in the snapshot-only Analyzer.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date, timedelta

from finops_agent.analyze import Evidence, Lead
from finops_agent.judge.brief import Brief, Candidate

BUSY_CPU_PCT = 10.0      # an hour counts as busy above this CPU
IDLE_SHARE_LEAD = 0.5    # instances busy less than this share of hours become idle-window leads
SKIP_LABELS = {"__name__", "job", "instance_id", "availability_zone"}


def usd(v):
    return f"${v:,.2f}"


def _tags(obj):
    return {t["Key"]: t["Value"] for t in obj.get("Tags", [])}


def _hours_ranges(hours):
    out, hs = [], sorted(hours)
    i = 0
    while i < len(hs):
        j = i
        while j + 1 < len(hs) and hs[j + 1] == hs[j] + 1:
            j += 1
        out.append(f"{hs[i]:02d}-{hs[j]:02d}")
        i = j + 1
    return ",".join(out) or "none"


class Ctx:
    def __init__(self, snap, col, days):
        self.snap, self.col, self.days = snap, col, days
        r = snap["resource_period"]
        self.res_days = (date.fromisoformat(r["End"]) - date.fromisoformat(r["Start"])).days
        self.start = date.fromisoformat(snap["period"]["Start"])
        self.end = date.fromisoformat(snap["period"]["End"])
        self.amortized = defaultdict(float)
        for b in snap["cost_by_resource_14d"]:
            for g in b["Groups"]:
                self.amortized[g["Keys"][0]] += float(g["Metrics"]["AmortizedCost"]["Amount"])
        self.inst = {i["InstanceId"]: i for i in snap["instances"]}
        self.metric_type = {n: v[0]["type"] for n, v in snap["metric_metadata"].items()}
        self._cpu = None

    def mcost(self, rid):
        """Amortized cost over the last 14 days, scaled to the analysis period."""
        return self.amortized.get(rid, 0.0) * self.days / self.res_days

    def at(self, d: date):
        return f"{d.isoformat()}T00:00:00Z"

    def q(self, query, at=None):
        return [(r["metric"], float(r["value"][1])) for r in self.col.prom_query(query, at)]

    def q1(self, query, at=None):
        r = self.q(query, at)
        return r[0][1] if r else None

    def hourly_cpu(self):
        """{instance_id: [cpu per hour]} over the whole period (one range query, cached)."""
        if self._cpu is None:
            data = self.col.prom("/api/v1/query_range", query="aws_ec2_cpuutilization_average",
                                 start=f"{self.start}T00:00:00Z", end=f"{self.end - timedelta(days=1)}T23:00:00Z", step="3600")
            self._cpu = {s["metric"]["instance_id"]: [float(v[1]) for v in s["values"]] for s in data["result"]}
        return self._cpu

    def sp_info(self, itype):
        fam = itype.split(".")[0]
        plans = [p for p in self.snap["savings_plans"] if p.get("ec2InstanceFamily") == fam and p.get("state", "active") == "active"]
        util = self.snap["sp_utilization"][-1]["Utilization"] if self.snap["sp_utilization"] else None
        return fam, plans, util

    def ids_regex(self, ids):
        return "|".join(sorted(ids))


# ---- lead generator ---------------------------------------------------------------------------
def idle_window_leads(cx: Ctx, start_n: int) -> list[Lead]:
    cpu = cx.hourly_cpu()
    groups = defaultdict(list)
    for iid, i in cx.inst.items():
        t = _tags(i)
        if i["State"]["Name"] != "running" or t.get("aws:autoscaling:groupName") or iid not in cpu:
            continue
        share = sum(1 for v in cpu[iid] if v > BUSY_CPU_PCT) / len(cpu[iid])
        if share < IDLE_SHARE_LEAD:
            groups[(i["InstanceType"], i["Placement"]["AvailabilityZone"], round(share / 0.05), t.get("aws:ec2launchtemplate:id", ""))].append(iid)
    leads = []
    for (itype, az, _, _), ids in sorted(groups.items(), key=lambda kv: sorted(kv[1])):
        ids = sorted(ids)
        share = sum(1 for v in cpu[ids[0]] if v > BUSY_CPU_PCT) / len(cpu[ids[0]])
        leads.append(Lead(f"L{start_n + len(leads) + 1:02d}",
                          f"{len(ids)} 台 {itype}（{az}）在 {share:.0%} 的小时里 CPU 高于 {BUSY_CPU_PCT:.0f}%，其余时间空闲",
                          "M4_downsize_schedule",
                          [Evidence("metrics", f"{len(ids)} 台实例按小时的 CPU，忙时占比 {share:.1%}", "query_range aws_ec2_cpuutilization_average step=1h")],
                          ["空闲是有规律的时段，还是持续低负载？", "它在保护什么（DR、容量、批处理）？", "停掉或按需起停，现金上能省多少？"],
                          kind="idle_window", params={"instances": ids}))
    return leads


# ---- gatherers --------------------------------------------------------------------------------
def build(lead: Lead, cx: Ctx) -> Brief:
    fn = {"cost_growth": _cost_growth, "unattributed_transfer": _transfer, "fleet_work": _fleet, "idle_window": _idle}.get(lead.kind)
    b = Brief(lead.id, lead.kind, lead.signal, lead.questions, default_step=lead.method_step)
    if fn is None:
        b.facts.append(Evidence("agent", "no evidence gatherer for this lead kind", ""))
        return b
    fn(lead, cx, b)
    return b


def _untrusted(cx, b, ids):
    for rid in ids:
        i = cx.inst.get(rid)
        if i:
            b.untrusted[rid] = {k: v for k, v in _tags(i).items() if not k.startswith("aws:")}


def _usage_row(cx, ut):
    for g in cx.snap["cost_by_usage_type"][0]["Groups"]:
        if g["Keys"][1] == ut:
            return float(g["Metrics"]["UnblendedCost"]["Amount"]), float(g["Metrics"]["UsageQuantity"]["Amount"])
    return 0.0, 0.0


def _daily(cx, ut):
    return [(d["TimePeriod"]["Start"], float(g["Metrics"]["UnblendedCost"]["Amount"]))
            for d in cx.snap["cost_daily_by_usage_type"] for g in d["Groups"] if g["Keys"][0] == ut]


def _counters(cx):
    return [n for n, t in cx.metric_type.items() if t == "counter"]


def _cost_growth(lead, cx, b):
    ut = lead.params["usage_type"]
    pts = _daily(cx, ut)
    vals = [v for _, v in pts]
    head, tail = sum(vals[:3]) / 3, sum(vals[-7:]) / 7
    since = date.fromisoformat(lead.since)
    cost, qty = _usage_row(cx, ut)
    unit = cost / qty if qty else 0.0
    excess, runrate = (tail - head) * cx.days, tail * cx.days
    b.facts += [
        Evidence("cost_explorer", f"{ut}：前 3 天平均 {usd(head)}/天，最近 7 天平均 {usd(tail)}/天，首个翻倍日 {lead.since}", "GetCostAndUsage DAILY by USAGE_TYPE"),
        Evidence("cost_explorer", f"{ut}：本周期 {usd(cost)}，用量 {qty:,.0f} GB，单价 ${unit:.4f}/GB", "GetCostAndUsage by USAGE_TYPE"),
        Evidence("computed", f"{ut} 当前月化 {usd(runrate)}，其中比基线多出的部分 {usd(excess)}（(最近 7 天均值 - 前 3 天均值) x {cx.days} 天）", "analysis"),
    ]
    nats = cx.snap["nat_gateways"]
    nat_ids = [n["NatGatewayId"] for n in nats]
    for n in nats:
        b.facts.append(Evidence("ec2", f"NAT 网关 {n['NatGatewayId']}，状态 {n['State']}，AZ/子网 {n.get('SubnetId', '?')}；近 14 天花费折合月化 {usd(cx.mcost(n['NatGatewayId']))}", "DescribeNatGateways + GetCostAndUsageWithResources"))
    eps = cx.snap["vpc_endpoints"]
    s3 = [e for e in eps if str(e.get("ServiceName", "")).endswith(".s3")]
    b.facts.append(Evidence("ec2", f"VPC endpoint 共 {len(eps)} 个，其中 S3 endpoint {len(s3)} 个", "DescribeVpcEndpoints"))
    b.facts.append(Evidence("pricing_knowledge", "S3 和 DynamoDB 的 gateway 类型 VPC endpoint 本身不收费；经 NAT 访问这两个服务的流量按 GB 收 NAT 处理费。NAT 处理费只能靠让流量不经过 NAT（endpoint）或减少流量来降", "AWS pricing"))
    before, after = cx.at(since), cx.at(since + timedelta(days=3))
    nat_metric = "aws_natgateway_bytes_out_to_destination_sum"
    if nat_metric in cx.metric_type:
        pre = cx.q1(f"sum(avg_over_time({nat_metric}[2d]))", before)
        post = cx.q1(f"sum(avg_over_time({nat_metric}[2d]))", after)
        if pre and post:
            b.facts.append(Evidence("metrics", f"NAT 出站字节每天：{since} 之前 2 天 {pre * 288 / 1e9:,.1f} GB，之后 3 天内 {post * 288 / 1e9:,.1f} GB，{post / pre:.1f} 倍", f"avg_over_time({nat_metric}[2d]) x 288"))
    # counters that moved with the cost: generic co-movement scan around the first anomalous day
    for name in sorted(_counters(cx)):
        series = cx.q(f"sum by (status,reason) (increase({name}[2d]))", before)
        series_after = {tuple(sorted(m.items())): v for m, v in cx.q(f"sum by (status,reason) (increase({name}[2d]))", after)}
        for m, v in series:
            key = tuple(sorted(m.items()))
            a = series_after.get(key)
            lbl = ",".join(f"{k}={x}" for k, x in sorted(m.items()) if x) or "-"
            if a is not None and (a > 0 or v > 0) and (v == 0 or abs(a / v - 1) > 1.0 or a == 0):
                b.facts.append(Evidence("metrics", f"{name}{{{lbl}}} 每天：{since} 之前 {v / 2:,.0f}，之后 {a / 2:,.0f}", f"sum by (status,reason) (increase({name}[2d])) @ {since} / {since + timedelta(days=3)}"))
    b.candidates += [
        Candidate("nat_excess_monthly", round(min(excess, cx.mcost(nat_ids[0]) if nat_ids else excess), 2), "billed_14d_extrapolated",
                  f"NAT 处理费里比基线多出的部分，月化（上限为 NAT 网关近期月化花费）"),
        Candidate("nat_all_bytes_monthly", round(runrate, 2), "billed_14d_extrapolated", "NAT 字节处理费当前全部月化（如果这条路径整体不走 NAT）"),
    ]
    b.resources = nat_ids
    b.resource_spend_usd = round(cx.mcost(nat_ids[0]), 2) if nat_ids else round(runrate, 2)
    b.default_step = "M6_architecture"
    b.scope = ("This lead covers the cost PATH. Whether the workload that drives the traffic is healthy is judged by a separate lead "
               "(fleet leads), so do not make 'fix the workload' your finding. Report what is structurally wrong with the path "
               "and would still bill per GB after the workload is fixed.")


def _transfer(lead, cx, b):
    ut = lead.params["usage_type"]
    cost, qty = _usage_row(cx, ut)
    unit = cost / qty if qty else 0.0
    b.facts.append(Evidence("cost_explorer", f"{ut}：本周期 {usd(cost)}，{qty:,.0f} GB，单价 ${unit:.4f}/GB，成本行没有资源 ID", "GetCostAndUsage by USAGE_TYPE"))
    # pair metrics: any counter carrying a `db` label links a client instance to a database service
    svc_az = defaultdict(set)
    for i in cx.inst.values():
        t = _tags(i)
        if i["State"]["Name"] == "running" and t.get("service"):
            svc_az[t["service"]].add((i["Placement"]["AvailabilityZone"], i["InstanceId"]))
    pair_total = defaultdict(float)
    cross = defaultdict(float)
    ids = set()
    for name in sorted(_counters(cx)):
        for m, v in cx.q(f"sum by (instance_id,db) (increase({name}[{cx.days}d]))", cx.at(cx.end)):
            if not m.get("db") or m["db"] not in svc_az or m["instance_id"] not in cx.inst:
                continue
            c = cx.inst[m["instance_id"]]
            caz = c["Placement"]["AvailabilityZone"]
            dbaz = {az for az, _ in svc_az[m["db"]]}
            pair_total[(m["instance_id"], caz, m["db"], tuple(sorted(dbaz)), name)] += v
            ids.add(m["instance_id"])
            ids |= {i for _, i in svc_az[m["db"]]}
            if caz not in dbaz:
                cross[(caz, tuple(sorted(dbaz)))] += v
    for (iid, caz, db, dbaz, name), v in sorted(pair_total.items()):
        b.facts.append(Evidence("metrics", f"{iid}（{caz}）-> 服务 {db}（{'、'.join(dbaz)}）：{name} 共 {v / 1e9:,.1f} GB / {cx.days} 天", f"sum by (instance_id,db) (increase({name}[{cx.days}d]))"))
    xgb = sum(cross.values()) / 1e9
    for (caz, dbaz), v in sorted(cross.items()):
        b.facts.append(Evidence("computed", f"跨 AZ 流量 {caz} <-> {'、'.join(dbaz)}：{v / 1e9:,.1f} GB / {cx.days} 天", "analysis"))
    if xgb:
        b.facts.append(Evidence("computed", f"跨 AZ 流量按账单单价 ${unit:.4f}/GB 折算：{usd(xgb * unit)} / 周期；账单上该用量类型共 {usd(cost)}（{qty:,.0f} GB）", "analysis"))
        b.candidates.append(Candidate("cross_az_cost_monthly", round(min(xgb * unit, cost), 2), "inferred",
                                      "跨 AZ 部分按账单单价折算的月成本；两端放进同一 AZ 后消失"))
    b.resources = sorted(ids)
    _untrusted(cx, b, b.resources)
    b.resource_spend_usd = round(cost, 2)
    b.default_step = "M6_architecture"


def _fleet(lead, cx, b):
    asg = lead.params["asg"]
    rec = next(a for a in cx.snap["asgs"] if a["AutoScalingGroupName"] == asg)
    members = sorted(iid for iid, i in cx.inst.items() if i["State"]["Name"] == "running" and _tags(i).get("aws:autoscaling:groupName") == asg)
    ids = cx.ids_regex(members)
    cost = sum(cx.mcost(m) for m in members)
    types = Counter(cx.inst[m]["InstanceType"] for m in members)
    azs = Counter(cx.inst[m]["Placement"]["AvailabilityZone"] for m in members)
    b.facts.append(Evidence("ec2", f"ASG {asg}：{len(members)} 台运行中，机型 {dict(types)}，AZ {dict(azs)}，min/max/desired {rec['MinSize']}/{rec['MaxSize']}/{rec['DesiredCapacity']}", "DescribeAutoScalingGroups"))
    b.facts.append(Evidence("cost_explorer", f"fleet 计算花费（amortized，近 14 天折合月化）{usd(cost)}，每台 {usd(cost / max(len(members), 1))}", "GetCostAndUsageWithResources"))
    sel = f'aws_ec2_cpuutilization_average{{instance_id=~"{ids}"}}'
    cpu = {"平均": cx.q1(f"avg(avg_over_time({sel}[{cx.days}d]))", cx.at(cx.end)),
           "p95": cx.q1(f"avg(quantile_over_time(0.95, {sel}[{cx.days}d]))", cx.at(cx.end)),
           "最大": cx.q1(f"max(max_over_time({sel}[{cx.days}d]))", cx.at(cx.end)),
           "最小": cx.q1(f"min(min_over_time({sel}[{cx.days}d]))", cx.at(cx.end))}
    b.facts.append(Evidence("metrics", "fleet CPU（整个周期，各台取平均）：" + "，".join(f"{k} {v:.1f}%" for k, v in cpu.items() if v is not None), "avg/quantile/max/min_over_time(aws_ec2_cpuutilization_average)"))
    series = cx.col.prom("/api/v1/series", **{"match[]": f'{{instance_id=~"{ids}"}}'})
    jobs = sorted({s.get("job", "") for s in series} - {""})
    b.facts.append(Evidence("metrics", f"这些实例上报的 job 标签：{jobs}", "series match instance_id"))
    groups = sorted({(s["__name__"], tuple(sorted((k, v) for k, v in s.items() if k not in SKIP_LABELS))) for s in series
                     if cx.metric_type.get(s["__name__"]) == "counter"})
    base_at, base_d = cx.at(cx.start + timedelta(days=3)), 3
    outcome = defaultdict(dict)
    for name, extra in groups:
        sel = name + "{" + ",".join([f'instance_id=~"{ids}"'] + [f'{k}="{v}"' for k, v in extra]) + "}"
        first = cx.q1(f"sum(increase({sel}[{base_d}d]))", base_at) or 0.0
        last = cx.q1(f"sum(increase({sel}[7d]))", cx.at(cx.end)) or 0.0
        lbl = ",".join(f"{k}={v}" for k, v in extra) or "-"
        b.facts.append(Evidence("metrics", f"{name}{{{lbl}}} 每天：周期前 {base_d} 天 {first / base_d:,.0f}，最近 7 天 {last / 7:,.0f}", f"sum(increase({name}[..])) @ {cx.start + timedelta(days=3)} and @ {cx.end}"))
        st = dict(extra).get("status")
        if st:
            outcome[name][st] = (first / base_d, last / 7)
    for name, d in outcome.items():
        for idx, label in ((0, f"周期前 {base_d} 天"), (1, "最近 7 天")):
            tot = sum(v[idx] for v in d.values())
            ok = sum(v[idx] for s, v in d.items() if s in ("succeeded", "success", "ok"))
            if tot > 0 and any(s in d for s in ("succeeded", "success", "ok")):
                b.facts.append(Evidence("computed", f"{name} 成功占比（{label}）：{ok / tot:.1%}（{ok:,.0f} / {tot:,.0f} 每天）", "analysis"))
    for lt in {rec.get("LaunchTemplate", {}).get("LaunchTemplateId")} - {None}:
        b.facts.append(Evidence("ec2", f"启动模板 {lt}", "DescribeAutoScalingGroups"))
    b.candidates.append(Candidate("fleet_compute_monthly", round(cost, 2), "billed_14d_extrapolated", "整个 fleet 的计算花费月化；只在这些实例确实没做有用的事时才算浪费"))
    b.resources = [asg] + members
    _untrusted(cx, b, members)
    b.resource_spend_usd = round(cost, 2)


def _idle(lead, cx, b):
    ids = lead.params["instances"]
    cpu = cx.hourly_cpu()
    n_h = len(cpu[ids[0]])
    series = cpu[ids[0]]
    t0 = cx.start
    busy = [v > BUSY_CPU_PCT for v in series]
    share = sum(busy) / n_h
    by_hour = defaultdict(lambda: [0, 0])
    by_wd = defaultdict(lambda: [0, 0])
    longest = run = 0
    for h, bz in enumerate(busy):
        d = t0 + timedelta(hours=h)
        by_hour[h % 24][0] += bz
        by_hour[h % 24][1] += 1
        wd = (t0 + timedelta(days=h // 24)).weekday() >= 5
        by_wd[wd][0] += bz
        by_wd[wd][1] += 1
        run = 0 if bz else run + 1
        longest = max(longest, run)
    busy_hours = [h for h, (a, n) in by_hour.items() if a / n >= 0.5]
    itype = cx.inst[ids[0]]["InstanceType"]
    cost = sum(cx.mcost(i) for i in ids)
    b.facts.append(Evidence("metrics", f"{len(ids)} 台 {itype}，每台的 CPU 按小时采样（{n_h} 个小时）：高于 {BUSY_CPU_PCT:.0f}% 的小时占 {share:.1%}，平均每天 {share * 24:.1f} 小时", "query_range aws_ec2_cpuutilization_average step=1h"))
    b.facts.append(Evidence("metrics", f"一天中多数天都忙的 UTC 小时：{_hours_ranges(busy_hours)}；工作日忙时占比 {by_wd[False][0] / by_wd[False][1]:.1%}，周末 {by_wd[True][0] / by_wd[True][1]:.1%}；最长连续空闲 {longest} 小时", "analysis of the hourly series"))
    lbls = cx.col.prom("/api/v1/series", **{"match[]": f'{{instance_id="{ids[0]}"}}'})
    b.facts.append(Evidence("metrics", f"该实例的指标：{sorted({s['__name__'] for s in lbls})}，job 标签 {sorted({s.get('job', '') for s in lbls} - {''})}", "series match instance_id"))
    b.facts.append(Evidence("cost_explorer", f"这组实例 amortized 近 14 天折合月化 {usd(cost)}（每台 {usd(cost / len(ids))}）", "GetCostAndUsageWithResources"))
    extra = []
    for i in ids:
        t = _tags(cx.inst[i])
        lt, asg = t.get("aws:ec2launchtemplate:id"), t.get("aws:autoscaling:groupName")
        if lt:
            users = [a["AutoScalingGroupName"] for a in cx.snap["asgs"] if a.get("LaunchTemplate", {}).get("LaunchTemplateId") == lt]
            extra.append(f"{i} 用启动模板 {lt}，它同时被 ASG {users or '无'} 使用")
        if asg:
            extra.append(f"{i} 属于 ASG {asg}")
    b.facts.append(Evidence("ec2", "；".join(extra) if extra else f"这组实例不属于任何 ASG，没有启动模板 tag；状态 running，启动于 {cx.inst[ids[0]].get('LaunchTime')}", "DescribeInstances"))
    fam, plans, util = cx.sp_info(itype)
    gross = cost * (1 - share)
    net = gross
    if plans and util:
        unused = float(util["UnusedCommitment"])
        b.facts.append(Evidence("savingsplans", f"机型族 {fam} 被 Savings Plan {[p['savingsPlanId'] for p in plans]} 覆盖；最近一个周期利用率 {float(util['UtilizationPercentage']):.2f}%，未用承诺 {usd(unused)}（承诺照付，被覆盖的用量停掉后现金不变）", "DescribeSavingsPlans + GetSavingsPlansUtilization"))
        net = max(0.0, gross - unused)
    else:
        b.facts.append(Evidence("savingsplans", f"机型族 {fam} 没有生效的 Savings Plan，停掉的小时按实际单价省钱", "DescribeSavingsPlans"))
    b.facts.append(Evidence("computed", f"空闲小时对应的 amortized 花费 {usd(gross)}（{usd(cost)} x 空闲占比 {1 - share:.1%}）", "analysis"))
    b.candidates.append(Candidate("idle_hours_cost", round(gross, 2), "inferred", "把空闲小时关掉，在不考虑承诺时对应的月化花费"))
    if plans and util:
        b.candidates.append(Candidate("net_after_commitment", round(net, 2), "inferred", "扣除 Savings Plan 未用承诺之后的现金节省（承诺付费不变）"))
    b.resources = list(ids)
    _untrusted(cx, b, ids)
    b.resource_spend_usd = round(cost, 2)
