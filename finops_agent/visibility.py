"""Visibility chain: four rings, each with its own output.

  ① requirements  config/visibility_requirements.yaml (goal-first, no metric lookups)
  ② plan          one search per needed signal: data source, query, what counts as found.
                  A need that names no metric (LLM-derived ring 1, c0020) is resolved here by `discover`:
                  candidate metric names found by meaning in the live server's metric catalogue.
  ③ search        execute exactly the plan, keep raw results as evidence
  ④ gaps          per SLI: covered / partial / missing, with the evidence behind it
"""
from __future__ import annotations

from pathlib import Path

import re

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


NO_CANDIDATE = "__no_candidate_found__"
MIN_HITS = 2          # a candidate must match at least this many distinct terms
REL_HITS = 0.5        # ... and at least this share of the best candidate's hits
MAX_CANDIDATES = 6
# Unit and statistic words fit many unrelated metrics ("utilization percent" is true of CPU and of memory).
# They may support a match but never carry it: a candidate needs at least one other term as anchor.
GENERIC = {"percent", "percentage", "utilization", "utilisation", "usage", "used", "total", "count", "rate", "sum",
           "average", "avg", "max", "min", "seconds", "second", "bytes", "byte", "number", "ratio", "per", "time", "data"}


def fetch_catalog(collector) -> dict[str, dict]:
    """The live server's metric catalogue: name -> {help, type, labels}. Metadata gives HELP text, series give labels."""
    meta = collector.prom("/api/v1/metadata")
    cat = {n: {"help": (m[0].get("help") or "") if m else "", "type": (m[0].get("type") or "") if m else "", "labels": set()}
           for n, m in meta.items()}
    for s in collector.prom("/api/v1/series", **{"match[]": '{__name__=~".+"}'}):
        e = cat.setdefault(s["__name__"], {"help": "", "type": "", "labels": set()})
        e["labels"].update(k for k in s if k != "__name__")
    return cat


def _term_hit(term: str, name: str, help_: str) -> bool:
    t = term.lower()
    hay = f"{name.lower()} {help_.lower()}"
    if len(t) >= 3:
        t = t[:-1] if t.endswith("s") and len(t) > 4 else t
        return t in hay
    return t in set(re.split(r"[^a-z0-9]+", hay))


def discover(need: dict, label: str, catalog: dict[str, dict]) -> list[dict]:
    """Candidate metric names for a need written as words (`terms`), by meaning, deterministic.
    A candidate matches >= MIN_HITS distinct terms (at least one not in GENERIC) in its name or HELP text, and
    carries the scope label."""
    terms = sorted({t.lower() for t in need.get("terms", [])})
    scored = []
    for name, e in catalog.items():
        if label and e["labels"] and label not in e["labels"]:
            continue
        hit = [t for t in terms if _term_hit(t, name, e["help"])]
        if len(hit) >= MIN_HITS and any(t not in GENERIC for t in hit):
            scored.append({"name": name, "hits": len(hit), "terms": hit})
    if not scored:
        return []
    best = max(c["hits"] for c in scored)
    keep = [c for c in scored if c["hits"] >= REL_HITS * best]
    keep.sort(key=lambda c: (-c["hits"], c["name"]))
    return keep[:MAX_CANDIDATES]


def ring2(reqs: list[dict], snap: dict, catalog: dict | None = None) -> list[dict]:
    plan = []
    for sli in reqs:
        for n, need in enumerate(sli["need"]):
            label, want = expected_scope(need["scope"], snap)
            step = {
                "id": f"{sli['id']}#{n}", "sli": sli["id"], "signal": need["signal"], "source": "prometheus",
                "query": {"path": "/api/v1/series", "match[]": f'{{__name__=~"{need.get("name")}"}}'},
                "found_if": f"series exist with label `{label}` covering {len(want)} expected values",
                "scope_label": label, "expected": sorted(want),
            }
            if "name" not in need:
                if catalog is None:
                    raise ValueError(f"{sli['id']}: need has no `name` and no metric catalogue was given to discover from")
                cands = discover(need, label, catalog)
                rx = "|".join(re.escape(c["name"]) for c in cands) or NO_CANDIDATE
                step["query"]["match[]"] = f'{{__name__=~"{rx}"}}'
                step["discovered"] = cands
            plan.append(step)
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


def ring4(reqs: list[dict], plan: list[dict], results: list[dict], mix: bool = False) -> list[dict]:
    """Per SLI: judge every need (covered / partial / missing), then roll up.
    mix=False (the reviewed path, unchanged): SLI status is the worst need.
    mix=True (derived rings): status is covered / partial / missing by share, and `mix` counts the needs, so one
    missing need does not erase the covered ones (c0017 lesson: a merged SLI was 'missing' for one bad need)."""
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
        if mix:
            counts = {k: sum(n["status"] == k for n in needs) for k in ("covered", "partial", "missing")}
            status = "covered" if counts["covered"] == len(needs) else ("missing" if counts["missing"] == len(needs) else "partial")
            rows.append({"sli": sli["id"], "decision": sli["decision"], "status": status, "mix": counts, "needs": needs})
            continue
        worst = "missing" if any(n["status"] == "missing" for n in needs) else ("partial" if any(n["status"] == "partial" for n in needs) else "covered")
        rows.append({"sli": sli["id"], "decision": sli["decision"], "status": worst, "needs": needs})
    return rows
