"""Visibility chain: four rings, each with its own output.

  ① requirements  config/visibility_requirements.yaml (goal-first, no metric lookups)
  ② plan          one search per needed signal: data source, query, what counts as found
  ③ search        execute exactly the plan, keep raw results as evidence
  ④ gaps          per SLI: covered / partial / missing, with the evidence behind it
"""
from __future__ import annotations

from pathlib import Path

import yaml

SCOPE_LABEL = {"running_instances": "instance_id", "nat_gateways": "nat_gateway_id"}


def ring1(path: Path) -> list[dict]:
    return yaml.safe_load(path.read_text())["slis"]


def expected_scope(scope: str, snap: dict) -> tuple[str, set]:
    if scope == "running_instances":
        return "instance_id", {i["InstanceId"] for i in snap["instances"] if i["State"]["Name"] == "running"}
    if scope == "nat_gateways":
        return "nat_gateway_id", {n["NatGatewayId"] for n in snap["nat_gateways"]}
    if scope.startswith("services:"):
        return "job", set(scope.split(":", 1)[1].split(","))
    raise ValueError(f"unknown scope {scope}")


def ring2(reqs: list[dict], snap: dict) -> list[dict]:
    plan = []
    for sli in reqs:
        for n, need in enumerate(sli["need"]):
            label, want = expected_scope(need["scope"], snap)
            plan.append({
                "id": f"{sli['id']}#{n}", "sli": sli["id"], "signal": need["signal"], "source": "prometheus",
                "query": {"path": "/api/v1/series", "match[]": f'{{__name__=~"{need["name"]}"}}'},
                "found_if": f"series exist with label `{label}` covering {len(want)} expected values",
                "scope_label": label, "expected": sorted(want),
            })
    return plan


def ring3(plan: list[dict], collector) -> list[dict]:
    results = []
    for step in plan:
        series = collector.prom("/api/v1/series", **{"match[]": step["query"]["match[]"]})
        names = sorted({s["__name__"] for s in series})
        covered = sorted({s.get(step["scope_label"]) for s in series if s.get(step["scope_label"])} & set(step["expected"]))
        if step["scope_label"] == "job":
            # job-scoped needs may be satisfied by app metrics that carry `job`
            covered = sorted({s.get("job") for s in series} & set(step["expected"]))
        results.append({"id": step["id"], "metric_names": names, "series_count": len(series), "covered": covered,
                        "query": step["query"]})
    return results


def ring4(reqs: list[dict], plan: list[dict], results: list[dict]) -> list[dict]:
    by_id = {r["id"]: r for r in results}
    rows = []
    for sli in reqs:
        steps = [p for p in plan if p["sli"] == sli["id"]]
        needs = []
        for p in steps:
            r = by_id[p["id"]]
            missing = sorted(set(p["expected"]) - set(r["covered"]))
            status = "covered" if not missing else ("missing" if not r["covered"] else "partial")
            needs.append({"signal": p["signal"], "status": status, "metrics": r["metric_names"],
                          "covered": len(r["covered"]), "expected": len(p["expected"]), "missing_scope": missing[:8],
                          "query": r["query"]["match[]"]})
        worst = "missing" if any(n["status"] == "missing" for n in needs) else ("partial" if any(n["status"] == "partial" for n in needs) else "covered")
        rows.append({"sli": sli["id"], "decision": sli["decision"], "status": worst, "needs": needs})
    return rows
