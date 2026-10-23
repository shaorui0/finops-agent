"""Analyze: deterministic detectors over a frozen snapshot.

Each detector maps to one step of docs/METHOD.md and returns Findings that
carry their own evidence. Detectors only use arithmetic and joins; anything
that needs judgment across sources is emitted as a Lead for the judgment
layer instead of being guessed here.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field

GP3_DISCOUNT = 0.20   # gp3 list price is 20% below gp2 per GB-month


@dataclass
class Evidence:
    source: str        # cost_explorer | ec2 | metrics | savingsplans
    what: str          # the fact, in one line
    ref: str = ""      # the call or query that produced it


@dataclass
class Finding:
    id: str
    type: str
    method_step: str
    title: str
    resources: list
    hops: list
    evidence: list
    monthly_savings_usd: float
    basis: str         # billed | billed_14d_extrapolated | list_price | inferred | none
    resource_spend_usd: float | None = None
    detector: str = ""

    def to_dict(self):
        d = asdict(self)
        d["evidence"] = [asdict(e) if isinstance(e, Evidence) else e for e in self.evidence]
        return d


@dataclass
class Lead:
    """A signal that needs cross-source judgment before it can become a finding."""
    id: str
    signal: str
    method_step: str
    evidence: list
    questions: list = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d["evidence"] = [asdict(e) if isinstance(e, Evidence) else e for e in self.evidence]
        return d


def _amt(metrics, key="UnblendedCost"):
    return float(metrics[key]["Amount"])


def _tags(obj):
    return {t["Key"]: t["Value"] for t in obj.get("Tags", [])}


class Analyzer:
    def __init__(self, snap: dict, days: int):
        self.s = snap
        self.days = days
        r = snap["resource_period"]
        from datetime import date
        self.res_days = (date.fromisoformat(r["End"]) - date.fromisoformat(r["Start"])).days
        self.findings: list[Finding] = []
        self.leads: list[Lead] = []
        self._n = 0
        self.resource_cost = defaultdict(float)
        for b in snap["cost_by_resource_14d"]:
            for g in b["Groups"]:
                self.resource_cost[g["Keys"][0]] += _amt(g["Metrics"])

    def _id(self):
        self._n += 1
        return f"F{self._n:02d}"

    def monthly(self, rid):
        """Resource cost over the last 14 days, scaled to the analysis period."""
        return self.resource_cost.get(rid, 0.0) * self.days / self.res_days

    def run(self):
        for fn in (self.spend_ranking, self.attribution, self.tag_vs_launch_template, self.unattached_volumes,
                   self.idle_public_ips, self.stopped_instance_storage, self.orphan_snapshots, self.gp2_volumes,
                   self.savings_plan_utilization, self.leads_from_cost_shape):
            fn()
        return self

    # ---- M2 -----------------------------------------------------------------
    def spend_ranking(self):
        groups = self.s["cost_by_service"][0]["Groups"]
        rows = sorted(((g["Keys"][0], _amt(g["Metrics"], "AmortizedCost")) for g in groups), key=lambda x: -x[1])
        total = sum(v for _, v in rows)
        self.ranking = {"total": total, "by_service": rows, "top_usage_types": []}
        ut = [(f"{g['Keys'][0]} / {g['Keys'][1]}", _amt(g["Metrics"])) for g in self.s["cost_by_usage_type"][0]["Groups"]]
        self.ranking["top_usage_types"] = sorted(ut, key=lambda x: -x[1])[:10]
        self.ranking["surprises"] = []
        svc = dict(rows)
        compute = svc.get("Amazon Elastic Compute Cloud - Compute", 0)
        other = svc.get("EC2 - Other", 0)
        if other > compute:
            self.ranking["surprises"].append(
                f"EC2 - Other (${other:,.0f}) is larger than EC2 compute (${compute:,.0f}): storage, NAT and data transfer dominate")

    # ---- M1 -----------------------------------------------------------------
    def attribution(self):
        groups = self.s["cost_by_owner"][0]["Groups"]
        untagged = sum(_amt(g["Metrics"]) for g in groups if g["Keys"][0] == "owner$")
        total = sum(_amt(g["Metrics"]) for g in groups)
        missing = [i["InstanceId"] for i in self.s["instances"] if "owner" not in _tags(i)]
        self.attribution_summary = {"untagged_usd": untagged, "total_usd": total,
                                    "untagged_share": untagged / total if total else 0, "instances_without_owner": missing}

    def tag_vs_launch_template(self):
        lt_owner = {}
        for ltv in self.s["launch_templates"]:
            lt_owner[ltv["LaunchTemplateId"]] = ltv
        for inst in self.s["instances"]:
            t = _tags(inst)
            lt = t.get("aws:ec2launchtemplate:id")
            asg = t.get("aws:autoscaling:groupName")
            if not lt or asg:
                continue
            ltv = lt_owner.get(lt)
            if not ltv:
                continue
            asg_using = [a["AutoScalingGroupName"] for a in self.s["asgs"] if a.get("LaunchTemplate", {}).get("LaunchTemplateId") == lt]
            members_service = {_tags(i).get("service") for i in self.s["instances"]
                               if _tags(i).get("aws:autoscaling:groupName") in asg_using}
            if members_service and t.get("service") not in members_service:
                self.findings.append(Finding(
                    self._id(), "misattributed_tags", "M1_visibility_attribution",
                    f"{inst['InstanceId']} is tagged service={t.get('service')} but launches from the template used by {', '.join(asg_using)} ({', '.join(sorted(members_service))})",
                    [inst["InstanceId"]],
                    ["instance tags name a service", "its launch template belongs to a different fleet", "cost is attributed to the wrong owner"],
                    [Evidence("ec2", f"tags service={t.get('service')} owner={t.get('owner')}", "DescribeInstances"),
                     Evidence("ec2", f"launch template {lt} is used by {asg_using}", "DescribeAutoScalingGroups")],
                    0.0, "none", self.monthly(inst["InstanceId"]), "tag_vs_launch_template"))

    # ---- M3 -----------------------------------------------------------------
    def unattached_volumes(self):
        for v in self.s["volumes"]:
            if v["State"] == "available":
                m = self.monthly(v["VolumeId"])
                self.findings.append(Finding(
                    self._id(), "unattached_volume", "M3_delete", f"{v['Size']} GB {v['VolumeType']} volume {v['VolumeId']} is not attached",
                    [v["VolumeId"]], ["state=available"],
                    [Evidence("ec2", f"state=available, created {v['CreateTime']}", "DescribeVolumes"),
                     Evidence("cost_explorer", f"${m:,.2f}/period", "GetCostAndUsageWithResources")],
                    m, "billed_14d_extrapolated", m, "unattached_volumes"))

    def idle_public_ips(self):
        for a in self.s["addresses"]:
            if not a.get("AssociationId"):
                m = self.monthly(a["AllocationId"])
                self.findings.append(Finding(
                    self._id(), "idle_public_ip", "M3_delete", f"Elastic IP {a['PublicIp']} is not associated",
                    [a["AllocationId"]], ["no association"],
                    [Evidence("ec2", "no AssociationId", "DescribeAddresses"),
                     Evidence("cost_explorer", f"${m:,.2f}/period", "GetCostAndUsageWithResources")],
                    m, "billed_14d_extrapolated", m, "idle_public_ips"))

    def stopped_instance_storage(self):
        vols = {v["VolumeId"]: v for v in self.s["volumes"]}
        for inst in self.s["instances"]:
            if inst["State"]["Name"] != "stopped":
                continue
            attached = [b["Ebs"]["VolumeId"] for b in inst.get("BlockDeviceMappings", []) if b.get("Ebs")]
            cost = sum(self.monthly(v) for v in attached)
            if not attached or cost <= 0:
                continue
            t = _tags(inst)
            desc = ", ".join(f"{vols[v]['Size']} GB {vols[v]['VolumeType']}" + (f" {vols[v]['Iops']} IOPS" if vols[v].get("Iops") else "")
                             for v in attached if v in vols)
            self.findings.append(Finding(
                self._id(), "stopped_instance_storage", "M3_delete",
                f"{t.get('Name', inst['InstanceId'])} has been stopped ({inst.get('StateTransitionReason', '')}); its volumes still bill",
                [inst["InstanceId"], *attached],
                ["instance compute cost is zero", "attached volumes carry the cost", "owner tag " + ("missing" if "owner" not in t else t["owner"])],
                [Evidence("ec2", f"state=stopped; {inst.get('StateTransitionReason', '')}", "DescribeInstances"),
                 Evidence("ec2", desc, "DescribeVolumes"),
                 Evidence("cost_explorer", f"volumes ${cost:,.2f}/period", "GetCostAndUsageWithResources")],
                cost, "billed_14d_extrapolated", cost, "stopped_instance_storage"))

    def orphan_snapshots(self):
        live_volumes = {v["VolumeId"] for v in self.s["volumes"]}
        used_images = {ltv["LaunchTemplateData"].get("ImageId") for ltv in self.s["launch_templates"]}
        used_images |= {i.get("ImageId") for i in self.s["instances"]}
        image_of = {}
        for img in self.s["images"]:
            for b in img.get("BlockDeviceMappings", []):
                if b.get("Ebs", {}).get("SnapshotId"):
                    image_of[b["Ebs"]["SnapshotId"]] = img["ImageId"]
        orphan, superseded = defaultdict(list), defaultdict(list)
        for sn in self.s["snapshots"]:
            img = image_of.get(sn["SnapshotId"])
            if img:
                if img not in used_images:
                    superseded[img].append(sn["SnapshotId"])
            elif sn["VolumeId"] not in live_volumes:
                orphan[sn["VolumeId"]].append(sn["SnapshotId"])
        snaps = [s for v in list(orphan.values()) + list(superseded.values()) for s in v]
        if not snaps:
            return
        cost = sum(self.monthly(s) for s in snaps)
        kept = sorted(used_images & set(image_of.values()))
        self.findings.append(Finding(
            self._id(), "orphan_snapshots", "M3_delete",
            f"{sum(len(v) for v in orphan.values())} snapshots of deleted volumes and {sum(len(v) for v in superseded.values())} snapshots of AMIs no template uses",
            sorted(orphan) + sorted(superseded),
            ["source volume no longer exists", "AMI not referenced by any launch template or instance", f"kept: {', '.join(kept)} (in use)"],
            [Evidence("ec2", f"orphans by source volume: { {k: len(v) for k, v in orphan.items()} }", "DescribeSnapshots + DescribeVolumes"),
             Evidence("ec2", f"superseded AMIs: {sorted(superseded)}", "DescribeImages + DescribeLaunchTemplateVersions"),
             Evidence("cost_explorer", f"${cost:,.2f}/period", "GetCostAndUsageWithResources")],
            cost, "billed_14d_extrapolated", cost, "orphan_snapshots"))

    # ---- M4 -----------------------------------------------------------------
    def gp2_volumes(self):
        for v in self.s["volumes"]:
            if v["VolumeType"] == "gp2" and v["State"] == "in-use":
                m = self.monthly(v["VolumeId"])
                self.findings.append(Finding(
                    self._id(), "gp2_to_gp3", "M4_downsize_schedule", f"{v['Size']} GB gp2 volume {v['VolumeId']} can move to gp3",
                    [v["VolumeId"]], ["volume type gp2", "gp3 is 20% cheaper per GB with equal or better baseline"],
                    [Evidence("ec2", f"type=gp2 size={v['Size']}", "DescribeVolumes"),
                     Evidence("cost_explorer", f"${m:,.2f}/period", "GetCostAndUsageWithResources")],
                    m * GP3_DISCOUNT, "list_price", m, "gp2_volumes"))

    # ---- M5 -----------------------------------------------------------------
    def savings_plan_utilization(self):
        rows = [(r["TimePeriod"]["Start"], float(r["Utilization"]["UtilizationPercentage"]), float(r["Utilization"]["UnusedCommitment"]))
                for r in self.s["sp_utilization"]]
        if not rows or rows[-1][1] >= 90:
            return
        plans = self.s["savings_plans"]
        fams = {p.get("ec2InstanceFamily") for p in plans if p.get("ec2InstanceFamily")}
        running = defaultdict(int)
        for i in self.s["instances"]:
            if i["State"]["Name"] == "running":
                running[i["InstanceType"].split(".")[0]] += 1
        self.findings.append(Finding(
            self._id(), "savings_plan_underutilized", "M5_commitment",
            f"Savings Plan utilization is {rows[-1][1]:.1f}% (${rows[-1][2]:,.0f} unused this period); do not buy more commitment",
            [p["savingsPlanId"] for p in plans],
            ["utilization by month: " + ", ".join(f"{d[:7]} {u:.1f}%" for d, u, _ in rows),
             f"plan families: {sorted(fams)}", f"running instances by family: {dict(running)}"],
            [Evidence("cost_explorer", f"utilization {[(d[:7], u) for d, u, _ in rows]}", "GetSavingsPlansUtilization"),
             Evidence("savingsplans", f"families {sorted(fams)}", "DescribeSavingsPlans"),
             Evidence("ec2", f"running by family {dict(running)}", "DescribeInstances")],
            0.0, "none", rows[-1][2], "savings_plan_utilization"))

    # ---- leads for the judgment layer --------------------------------------
    def leads_from_cost_shape(self):
        days = self.s["cost_daily_by_usage_type"]
        series = defaultdict(list)
        for d in days:
            for g in d["Groups"]:
                series[g["Keys"][0]].append((d["TimePeriod"]["Start"], _amt(g["Metrics"])))
        for ut, pts in series.items():
            vals = [v for _, v in pts]
            if len(vals) < 7 or max(vals) < 5:
                continue
            head, tail = sum(vals[:3]) / 3, sum(vals[-7:]) / 7
            if head > 0 and tail / head > 2:
                jump = next(d for d, v in pts if v > head * 2)
                self.leads.append(Lead(f"L{len(self.leads) + 1:02d}", f"{ut} rose {tail / head:.1f}x, starting {jump}", "M2_ranking",
                                       [Evidence("cost_explorer", f"{ut}: first 3 days avg ${head:,.2f}/day, last 7 days ${tail:,.2f}/day", "GetCostAndUsage DAILY by USAGE_TYPE")],
                                       ["what changed on that day?", "which workloads send this traffic?", "is the path itself avoidable?"]))
        for g in self.s["cost_by_usage_type"][0]["Groups"]:
            svc, ut = g["Keys"]
            if "DataTransfer-Regional" in ut and _amt(g["Metrics"]) > 50:
                self.leads.append(Lead(f"L{len(self.leads) + 1:02d}", f"{ut} costs ${_amt(g['Metrics']):,.0f} with no resource id", "M6_architecture",
                                       [Evidence("cost_explorer", f"{svc} / {ut} ${_amt(g['Metrics']):,.2f}, quantity {float(g['Metrics']['UsageQuantity']['Amount']):,.0f} GB", "GetCostAndUsage by USAGE_TYPE")],
                                       ["which instance pairs sit in different AZs and talk to each other?", "is there a per-flow metric?"]))
        busy = defaultdict(list)
        for i in self.s["instances"]:
            t = _tags(i)
            if i["State"]["Name"] == "running" and t.get("aws:autoscaling:groupName"):
                busy[t["aws:autoscaling:groupName"]].append(i["InstanceId"])
        for asg, ids in busy.items():
            self.leads.append(Lead(f"L{len(self.leads) + 1:02d}", f"{asg}: {len(ids)} instances; is the fleet doing useful work?", "M3_delete",
                                   [Evidence("ec2", f"{len(ids)} running instances", "DescribeAutoScalingGroups")],
                                   ["CPU says busy, but what is the success rate of the work?"]))


def check_invariants(findings: list[Finding]) -> list[str]:
    """Violations of the hard rules in docs/METHOD.md."""
    out = []
    for f in findings:
        if f.resource_spend_usd is not None and f.monthly_savings_usd > f.resource_spend_usd + 0.01:
            out.append(f"{f.id}: savings ${f.monthly_savings_usd:,.2f} exceed resource spend ${f.resource_spend_usd:,.2f}")
        if f.monthly_savings_usd > 0 and f.basis == "none":
            out.append(f"{f.id}: non-zero savings without a basis")
        if not f.evidence:
            out.append(f"{f.id}: no evidence")
    return out
