"""FinOps SLOs: compute SLIs per run, diff findings across runs, export metrics.

A one-off cleanup decays. This module turns each run into a measurement:
SLI values against targets, a waste budget, and a state diff that marks
findings as new / persisting / resolved / regressed. `regressed` (a resource
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
    evidence["waste_ratio"] = f"${waste:,.2f} billed-basis savings open / ${spend:,.2f} spend"

    a = result["attribution"]
    vals["attribution_coverage"] = 1 - a["untagged_share"]
    evidence["attribution_coverage"] = f"${a['untagged_usd']:,.2f} of ${a['total_usd']:,.2f} has no owner tag"

    sp = snap.get("sp_utilization") or []
    if sp:
        u = sp[-1]["Utilization"]
        vals["commitment_utilization"] = float(u["UtilizationPercentage"]) / 100
        evidence["commitment_utilization"] = f"{u['UtilizationPercentage']}% in {sp[-1]['TimePeriod']['Start'][:7]}, ${float(u['UnusedCommitment']):,.2f} unused"

    live = {v["VolumeId"] for v in snap["volumes"]}
    ages = [(_age_days(v["CreateTime"], run_date), v["VolumeId"]) for v in snap["volumes"] if v["State"] == "available"]
    ages += [(_age_days(s["StartTime"], run_date), s["SnapshotId"]) for s in snap["snapshots"]
             if s["VolumeId"] not in live and "CreateImage" not in s.get("Description", "")]
    if ages:
        age, rid = max(ages)
        vals["orphan_max_age_days"] = age
        evidence["orphan_max_age_days"] = f"oldest orphan {rid}, {age} days"

    starts = []
    for l in result["leads"]:
        if "starting " in l["signal"]:
            starts.append((_age_days(l["signal"].rsplit("starting ", 1)[1], run_date), l["signal"]))
    if starts:
        lag, sig = max(starts)
        vals["anomaly_time_to_detect_days"] = lag
        evidence["anomaly_time_to_detect_days"] = f"{sig}; first reported by this run, {lag} days later"

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
            evidence["useful_work_ratio"] = f"worst fleet {job}: {worst:.1%} of jobs succeeded in the last day"

    gaps = result["visibility"]["gaps"]
    vals["visibility_coverage"] = sum(g["status"] == "covered" for g in gaps) / len(gaps) if gaps else 1.0
    evidence["visibility_coverage"] = ", ".join(f"{g['sli']}={g['status']}" for g in gaps if g["status"] != "covered") or "all covered"

    if state:
        first_seen = state.get("first_seen", {})
        open_ages = [(_age_days(first_seen[_key(f)], run_date), f["id"]) for f in result["findings"] if _key(f) in first_seen]
        if open_ages:
            age, fid = max(open_ages)
            vals["remediation_age_days"] = age
            evidence["remediation_age_days"] = f"{fid} open for {age} days"
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
        row = {"id": s["id"], "what": s["what"], "op": s["op"], "target": s["target"], "value": v,
               "status": status, "cadence": s["cadence"], "evidence": slis["evidence"].get(s["id"], "")}
        if s.get("budget"):
            budget = s["target"] * slis["spend"]
            row["budget_usd"] = budget
            row["budget_used"] = slis["waste"] / budget if budget else None
        rows.append(row)
    return rows


def diff_state(findings: list[dict], state: dict | None, run_id: str, run_date: date) -> tuple[dict, dict]:
    """Compare this run with the previous state. Returns (diff, new_state)."""
    state = state or {"runs": [], "first_seen": {}, "resolved": {}}
    prev_open = set(state.get("open", []))
    resolved = dict(state.get("resolved", {}))
    first_seen = dict(state.get("first_seen", {}))
    now = {_key(f): f for f in findings}
    diff = {"new": [], "persisting": [], "resolved": [], "regressed": []}
    for k, f in now.items():
        if k in resolved:
            diff["regressed"].append({"key": k, "finding": f["id"], "resolved_in": resolved.pop(k)})
        elif k in prev_open:
            diff["persisting"].append({"key": k, "finding": f["id"], "since": first_seen.get(k)})
        else:
            diff["new"].append({"key": k, "finding": f["id"]})
        first_seen.setdefault(k, run_date.isoformat())
    for k in prev_open - set(now):
        diff["resolved"].append({"key": k})
        resolved[k] = run_id
    new_state = {"runs": state.get("runs", []) + [run_id], "open": sorted(now), "first_seen": first_seen, "resolved": resolved}
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


def load_cfg(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def load_state(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None
