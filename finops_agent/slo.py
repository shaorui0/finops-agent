"""FinOps SLOs: compute SLIs per run, diff findings across runs, export metrics.

A one-off cleanup decays. This module turns each run into a measurement:
SLI values against targets, a waste budget, and a state diff that marks
findings as new / persisting / resolved / not_redetected / regressed. `regressed` (a resource
that was fixed and came back) is the clearest sign that the system is rotting.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

BILLED = ("billed", "billed_14d_extrapolated")


def _key(f):
    return f"{f['type']}|{','.join(sorted(f['resources']))}"


def _age_days(ts: str, now: date) -> float:
    d = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).date()
    return (now - d).days


def compute_slis(result: dict, snap: dict, collector, run_date: date, state: dict | None) -> dict:
    spend = result["ranking"]["total"]
    vals, evidence = {}, {}

    waste = sum(f["monthly_savings_usd"] for f in result["findings"] if f["basis"] in BILLED)
    vals["waste_ratio"] = waste / spend if spend else 0.0
    evidence["waste_ratio"] = f"未处理的账单口径节省 ${waste:,.2f} / 花费 ${spend:,.2f}"

    a = result["attribution"]
    vals["attribution_coverage"] = 1 - a["untagged_share"]
    evidence["attribution_coverage"] = f"${a['total_usd']:,.2f} 中有 ${a['untagged_usd']:,.2f} 没有 owner tag"

    sp = snap.get("sp_utilization") or []
    if sp:
        u = sp[-1]["Utilization"]
        vals["commitment_utilization"] = float(u["UtilizationPercentage"]) / 100
        evidence["commitment_utilization"] = f"{sp[-1]['TimePeriod']['Start'][:7]} 利用率 {u['UtilizationPercentage']}%，${float(u['UnusedCommitment']):,.2f} 未用"

    live = {v["VolumeId"] for v in snap["volumes"]}
    ages = [(_age_days(v["CreateTime"], run_date), v["VolumeId"]) for v in snap["volumes"] if v["State"] == "available"]
    ages += [(_age_days(s["StartTime"], run_date), s["SnapshotId"]) for s in snap["snapshots"]
             if s["VolumeId"] not in live and "CreateImage" not in s.get("Description", "")]
    if ages:
        age, rid = max(ages)
        vals["orphan_max_age_days"] = age
        evidence["orphan_max_age_days"] = f"最老的孤儿 {rid}，{age} 天"

    starts = [(_age_days(l["since"], run_date), l["signal"]) for l in result["leads"] if l.get("since")]
    if starts:
        lag, sig = max(starts)
        vals["anomaly_time_to_detect_days"] = lag
        evidence["anomaly_time_to_detect_days"] = f"{sig}；本次运行首次报出，晚了 {lag} 天"

    if collector is not None:
        at = f"{run_date.isoformat()}T00:00:00Z"
        ok = collector.prom_query('sum by (job) (increase(ingest_jobs_total{status="succeeded"}[1d]))', at)
        tot = collector.prom_query("sum by (job) (increase(ingest_jobs_total[1d]))", at)
        okm = {r["metric"].get("job"): float(r["value"][1]) for r in ok}
        ratios = {r["metric"].get("job"): okm.get(r["metric"].get("job"), 0.0) / float(r["value"][1])
                  for r in tot if float(r["value"][1]) > 0}
        if ratios:
            job, worst = min(ratios.items(), key=lambda x: x[1])
            vals["useful_work_ratio"] = worst
            evidence["useful_work_ratio"] = f"最差的 fleet {job}：最近一天 {worst:.1%} 的 job 成功"

    gaps = result["visibility"]["gaps"]
    vals["visibility_coverage"] = sum(g["status"] == "covered" for g in gaps) / len(gaps) if gaps else 1.0
    evidence["visibility_coverage"] = ", ".join(f"{g['sli']}={g['status']}" for g in gaps if g["status"] != "covered") or "全部覆盖"

    if state:
        first_seen = state.get("first_seen", {})
        open_ages = [(_age_days(first_seen[_key(f)], run_date), f["id"]) for f in result["findings"] if _key(f) in first_seen]
        if open_ages:
            age, fid = max(open_ages)
            vals["remediation_age_days"] = age
            evidence["remediation_age_days"] = f"{fid} 已持续 {age} 天未处理"
    return {"values": vals, "evidence": evidence, "spend": spend, "waste": waste}


def evaluate(slis: dict, cfg: dict) -> list[dict]:
    rows = []
    for s in cfg["slos"]:
        v = slis["values"].get(s["id"])
        if v is None:
            status = "no_data"
        else:
            good = v >= s["target"] if s["op"] == ">=" else v <= s["target"]
            status = "ok" if good else "violated"
        row = {"id": s["id"], "what": s["what"], "unit": s.get("unit", "ratio"), "op": s["op"], "target": s["target"], "value": v,
               "status": status, "cadence": s["cadence"], "evidence": slis["evidence"].get(s["id"], "")}
        if s.get("budget"):
            budget = s["target"] * slis["spend"]
            row["budget_usd"] = budget
            row["budget_used"] = slis["waste"] / budget if budget else None
        rows.append(row)
    return rows


COST_DROP = 0.9                  # a resource whose daily cost fell below this share of what it was when detected has changed


def _inventory(snap: dict) -> dict:
    """resource id -> the attributes whose change means someone touched the resource."""
    out = {}
    for i in snap.get("instances", []):
        out[i["InstanceId"]] = (i["State"]["Name"], i.get("InstanceType"))
    for v in snap.get("volumes", []):
        out[v["VolumeId"]] = (v["State"], v.get("VolumeType"), v.get("Size"), v.get("Iops"), len(v.get("Attachments", [])))
    for a in snap.get("addresses", []):
        out[a["AllocationId"]] = (bool(a.get("AssociationId")),)
    for x in snap.get("snapshots", []):
        out[x["SnapshotId"]] = ("snapshot",)
    for x in snap.get("images", []):
        out[x["ImageId"]] = ("image",)
    for g in snap.get("asgs", []):
        out[g["AutoScalingGroupName"]] = (g.get("DesiredCapacity"),)
    for p in snap.get("savings_plans", []):
        out[p["savingsPlanId"]] = (p.get("state"), p.get("commitment"))
    for n in snap.get("nat_gateways", []):
        out[n["NatGatewayId"]] = (n["State"],)
    return out


def _evidence(snap: dict, key: str) -> dict:
    """Cost-side and inventory-side facts for every resource of a finding key, as of this snapshot."""
    inv = _inventory(snap)
    r = snap["resource_period"]
    res_days = max(1, (date.fromisoformat(r["End"]) - date.fromisoformat(r["Start"])).days)
    cost = {}
    for b in snap.get("cost_by_resource_14d", []):
        for g in b["Groups"]:
            cost[g["Keys"][0]] = cost.get(g["Keys"][0], 0.0) + float(g["Metrics"]["UnblendedCost"]["Amount"])
    return {rid: {"present": rid in inv, "attrs": list(inv.get(rid, ())), "cost_day": round(cost.get(rid, 0.0) / res_days, 6)}
            for rid in key.split("|", 1)[1].split(",")}


def _verdict(key: str, prev_ev: dict | None, snap: dict) -> tuple[str, str]:
    """('resolved' | 'not_redetected', reason) for a finding that was not reported this run.

    resolved = the resource is gone from the inventory, or its attributes/cost changed since it was detected.
    not_redetected = at least one resource that was there is still there, unchanged and still billing: the finding
    disappeared but the thing it was about did not, so a missed detection must not be recorded as a fix."""
    now = _evidence(snap, key)
    if not prev_ev:
        still = [r for r, e in now.items() if e["present"]]
        return ("not_redetected", f"{','.join(still)} 仍在账号里，没有检测时的基线可比") if still else ("resolved", "资源已不在清单里")
    unchanged = []
    for rid, before in prev_ev.items():
        if not before.get("present"):
            continue
        n = now.get(rid) or {"present": False, "attrs": [], "cost_day": 0.0}
        if not n["present"]:
            continue
        cost_dropped = before["cost_day"] > 0 and n["cost_day"] < before["cost_day"] * COST_DROP
        if n["attrs"] == before["attrs"] and not cost_dropped:
            unchanged.append(rid)
    if unchanged:
        return "not_redetected", f"{','.join(unchanged)} 仍在清单里，属性和成本与检测时一致"
    return "resolved", "资源已不在清单里，或属性/成本已变化"


def diff_state(findings: list[dict], state: dict | None, run_id: str, run_date: date, snap: dict | None = None) -> tuple[dict, dict]:
    """Compare this run with the previous state. Returns (diff, new_state).

    A finding that is gone is `resolved` only with cost-side evidence that the resource or its usage changed; if the
    resource is still there and still costs the same it is `not_redetected` (a missed detection, not a fix). Without a
    snapshot (callers that predate this) every gone finding is `resolved`, the old behavior."""
    state = state or {"runs": [], "first_seen": {}, "resolved": {}}
    prev_open = set(state.get("open", []))
    missed = dict(state.get("not_redetected", {}))
    ev = dict(state.get("evidence", {}))
    resolved = dict(state.get("resolved", {}))
    first_seen = dict(state.get("first_seen", {}))
    now = {_key(f): f for f in findings}
    diff = {"new": [], "persisting": [], "resolved": [], "regressed": [], "not_redetected": []}
    for k, f in now.items():
        if k in resolved:
            diff["regressed"].append({"key": k, "finding": f["id"], "resolved_in": resolved.pop(k)})
        elif k in prev_open or k in missed:
            diff["persisting"].append({"key": k, "finding": f["id"], "since": first_seen.get(k)})
        else:
            diff["new"].append({"key": k, "finding": f["id"]})
        missed.pop(k, None)
        first_seen.setdefault(k, run_date.isoformat())
        if snap is not None:
            ev[k] = _evidence(snap, k)
    for k in sorted((prev_open | set(missed)) - set(now)):
        verdict, why = _verdict(k, ev.get(k), snap) if snap is not None else ("resolved", "")
        if verdict == "resolved":
            diff["resolved"].append({"key": k})
            resolved[k] = run_id
            missed.pop(k, None)
            ev.pop(k, None)
        else:
            missed.setdefault(k, run_id)
            diff["not_redetected"].append({"key": k, "since": missed[k], "why": why})
    new_state = {"runs": state.get("runs", []) + [run_id], "open": sorted(now), "first_seen": first_seen, "resolved": resolved,
                 "not_redetected": missed, "evidence": {k: v for k, v in ev.items() if k in now or k in missed}}
    return diff, new_state


def to_prometheus(rows: list[dict], diff: dict, run_id: str, ts: float) -> str:
    """Prometheus text exposition, for the node_exporter textfile collector or a pushgateway."""
    out = ["# HELP finops_last_run_timestamp_seconds When the latest inspection run finished",
           "# TYPE finops_last_run_timestamp_seconds gauge", f"finops_last_run_timestamp_seconds {ts:.0f}",
           "# HELP finops_sli FinOps SLI value for the latest run", "# TYPE finops_sli gauge"]
    for r in rows:
        if r["value"] is not None:
            out.append(f'finops_sli{{sli="{r["id"]}",run="{run_id}"}} {float(r["value"]):.6g}')
    out += ["# HELP finops_slo_target FinOps SLO target", "# TYPE finops_slo_target gauge"]
    out += [f'finops_slo_target{{sli="{r["id"]}",op="{r["op"]}"}} {r["target"]}' for r in rows]
    out += ["# HELP finops_findings Findings by lifecycle state compared with the previous run", "# TYPE finops_findings gauge"]
    out += [f'finops_findings{{state="{k}"}} {len(v)}' for k, v in diff.items()]
    b = next((r for r in rows if "budget_usd" in r), None)
    if b:
        out += ["# HELP finops_waste_budget_used Share of the monthly waste budget consumed", "# TYPE finops_waste_budget_used gauge",
                f"finops_waste_budget_used {b['budget_used']:.6g}",
                "# HELP finops_waste_budget_usd Monthly waste budget (SLO target x spend)", "# TYPE finops_waste_budget_usd gauge",
                f"finops_waste_budget_usd {b['budget_usd']:.6g}",
                "# HELP finops_waste_usd Open waste with billed-basis evidence", "# TYPE finops_waste_usd gauge",
                f"finops_waste_usd {b['budget_used'] * b['budget_usd']:.6g}"]
    return "\n".join(out) + "\n"


def fmt(value, unit: str) -> str:
    if value is None:
        return "—"
    return f"{value:.1%}" if unit == "ratio" else f"{value:g} 天"


def load_cfg(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def load_state(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None
