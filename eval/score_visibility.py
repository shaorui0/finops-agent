"""Score an LLM-derived ring 1 against the human-reviewed one (config/visibility_requirements.yaml).

Matching rule (need level). A reviewed need R is covered by a derived need D when both hold:
  scope  the scopes overlap: same kind (running_instances / nat_gateways), or both `services:` lists
         sharing at least one service. `running_instances` and `services:` never overlap (strict).
  name   the regexes match at least one common metric name from the universe, where
         universe = every metric name on the test metrics server  U  a small PROBE list of plausible names
         for signals the server does not have (memory, processed bytes), so that a reviewed need that is a
         planted gap can still be compared. Full match, like Prometheus. A derived regex that matches more
         than half of the universe is treated as a wildcard and never counts.
Reported numbers:
  recall     reviewed needs covered / reviewed needs                     (the "overlap", target >= 0.8)
  precision  derived needs that cover some reviewed need / derived needs
  name-only  recall with the scope condition dropped (how much is lost to scope vocabulary alone)
  SLI level  a reviewed SLI is covered if all its needs are covered, partial if some
There is deliberately no semantic "same decision class" fallback: it needs a judge, and a judge would make
the score depend on a second model.

    python3 -m eval.score_visibility --derived runs/ring1_llm.yaml [--prom http://127.0.0.1:33566]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REVIEWED = ROOT / "config" / "visibility_requirements.yaml"

PROBES = ["node_memory_MemAvailable_bytes", "node_memory_MemTotal_bytes", "aws_ec2_memory_utilization",
          "mem_used_percent", "CWAgent_mem_used_percent", "aws_cwagent_mem_used_percent",
          "ingest_bytes_processed_total", "ingest_records_processed_total", "etl_records_processed_total"]
WILDCARD_SHARE = 0.5


def server_metric_names(prom: str | None = None) -> set[str]:
    """Metric names on the test metrics server: over HTTP when `prom` is given, else in-process."""
    if prom:
        q = urllib.parse.urlencode({"match[]": '{__name__=~".+"}'})
        with urllib.request.urlopen(f"{prom.rstrip('/')}/api/v1/series?{q}", timeout=30) as r:
            return {s["__name__"] for s in json.load(r)["data"]}
    from testenv import metrics_server
    return {s.labels["__name__"] if "__name__" in s.labels else s.name for s in metrics_server.build()[1]}


def parse_scope(scope: str) -> tuple[str, frozenset]:
    if scope.startswith("services:"):
        return "services", frozenset(scope.split(":", 1)[1].split(","))
    return scope, frozenset()


def scope_overlap(a: str, b: str) -> bool:
    ka, sa = parse_scope(a)
    kb, sb = parse_scope(b)
    return ka == kb and (ka != "services" or bool(sa & sb))


def matches(regex: str, universe: set[str]) -> set[str]:
    try:
        return {u for u in universe if re.fullmatch(regex, u)}
    except re.error:
        return set()


def name_overlap(reviewed: str, derived: str, universe: set[str]) -> bool:
    d = matches(derived, universe)
    if len(d) > WILDCARD_SHARE * len(universe):
        return False
    return bool(matches(reviewed, universe) & d)


def score(reviewed: list[dict], derived: list[dict], names: set[str]) -> dict:
    universe = set(names) | set(PROBES)
    dneeds = [(s["id"], n) for s in derived for n in s["need"]]
    rows, total, hit, hit_name = [], 0, 0, 0
    used = set()
    for s in reviewed:
        cov = []
        for n in s["need"]:
            by = [(sid, i) for i, (sid, d) in enumerate(dneeds)
                  if scope_overlap(n["scope"], d["scope"]) and name_overlap(n["name"], d["name"], universe)]
            by_name = [1 for sid, d in dneeds if name_overlap(n["name"], d["name"], universe)]
            used.update(i for _, i in by)
            cov.append({"signal": n["signal"], "name": n["name"], "scope": n["scope"], "covered": bool(by),
                        "by": sorted({sid for sid, _ in by}), "name_only": bool(by_name)})
        total += len(cov)
        hit += sum(c["covered"] for c in cov)
        hit_name += sum(c["name_only"] for c in cov)
        k = sum(c["covered"] for c in cov)
        rows.append({"sli": s["id"], "needs": cov, "covered": k, "of": len(cov),
                     "status": "covered" if k == len(cov) else ("partial" if k else "missed")})
    extra = []
    for i, (sid, d) in enumerate(dneeds):
        if i in used:
            continue
        real = matches(d["name"], set(names))
        extra.append({"sli": sid, "name": d["name"], "scope": d["scope"], "real_metrics": sorted(real),
                      "kind": "matches real metrics, not in reviewed" if real else "matches no metric on the server"})
    return {"recall": hit / total if total else 0.0, "recall_name_only": hit_name / total if total else 0.0,
            "precision": len(used) / len(dneeds) if dneeds else 0.0,
            "reviewed_needs": total, "covered_needs": hit, "derived_needs": len(dneeds), "matched_derived": len(used),
            "sli_covered": sum(r["status"] == "covered" for r in rows), "reviewed_slis": len(rows),
            "rows": rows, "extra": extra}


def render(res: dict) -> str:
    out = [f"overlap (recall of reviewed needs): {res['covered_needs']}/{res['reviewed_needs']} = {res['recall']:.2f}   "
           f"(target >= 0.80)",
           f"name-only recall (scope ignored):   {res['recall_name_only']:.2f}",
           f"precision: {res['matched_derived']}/{res['derived_needs']} = {res['precision']:.2f}",
           f"reviewed SLIs fully covered: {res['sli_covered']}/{res['reviewed_slis']}", "",
           f"{'reviewed SLI':<24}{'needs':<7}{'status':<9}covered by (derived SLI ids)"]
    for r in res["rows"]:
        by = sorted({b for n in r["needs"] for b in n["by"]})
        miss = [n["name"] for n in r["needs"] if not n["covered"]]
        out.append(f"{r['sli']:<24}{r['covered']}/{r['of']:<5}{r['status']:<9}{', '.join(by) or '-'}"
                   + (f"   missed: {', '.join(miss)}" if miss else ""))
    out += ["", "derived needs that cover no reviewed need:"]
    out += [f"  {e['sli']}: {e['name']} [{e['scope']}] -> {e['kind']}" for e in res["extra"]] or ["  (none)"]
    return "\n".join(out)


def run_rings(slis: list[dict], snap: dict, prom: str) -> dict:
    """Rings 2-4 (finops_agent.visibility) for one ring-1 list against the live test metrics server."""
    from finops_agent import visibility
    from finops_agent.collect import Collector, Config, Trace
    col = Collector(Config(aws_endpoint=None, prom_url=prom), Trace())
    plan = visibility.ring2(slis, snap)
    return {g["sli"]: g for g in visibility.ring4(slis, plan, visibility.ring3(plan, col))}


def gap_table(reviewed: list[dict], derived: list[dict], snap: dict, prom: str) -> str:
    """Gap table of the reviewed ring 1 next to the derived one. Derived SLIs are shown under the reviewed SLI
    that shares a need with them (strict rule above); the rest are listed as derived-only."""
    rg, dg = run_rings(reviewed, snap, prom), run_rings(derived, snap, prom)
    names = server_metric_names(prom) | set(PROBES)
    out = [f"{'ring-4 status':<14}{'reviewed SLI':<24}{'derived SLI (status)':<62}"]
    claimed = set()
    for s in reviewed:
        ds = [d["id"] for d in derived if any(scope_overlap(n["scope"], m["scope"]) and name_overlap(n["name"], m["name"], names)
                                              for n in s["need"] for m in d["need"])]
        claimed.update(ds)
        cell = ", ".join(f"{d} ({dg[d]['status']})" for d in ds) or "-"
        out.append(f"{rg[s['id']]['status']:<14}{s['id']:<24}{cell}")
    only = [d["id"] for d in derived if d["id"] not in claimed]
    out += ["", "derived-only SLIs: " + (", ".join(f"{d} ({dg[d]['status']})" for d in only) or "(none)")]
    cnt = lambda g: {k: sum(v["status"] == k for v in g.values()) for k in ("covered", "partial", "missing")}
    out += [f"reviewed ring-4 totals: {cnt(rg)}", f"derived  ring-4 totals: {cnt(dg)}"]
    return "\n".join(out)


def load(path) -> list[dict]:
    return yaml.safe_load(Path(path).read_text())["slis"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="eval.score_visibility")
    ap.add_argument("--derived", required=True)
    ap.add_argument("--reviewed", default=str(REVIEWED))
    ap.add_argument("--prom", default=None, help="metrics server URL; default: in-process testenv")
    ap.add_argument("--snapshot", default=None, help="snapshot.json from a run; with --prom, also run rings 2-4")
    ap.add_argument("--json", default=None, help="also write the full result here")
    a = ap.parse_args(argv)
    res = score(load(a.reviewed), load(a.derived), server_metric_names(a.prom))
    print(render(res))
    if a.snapshot and a.prom:
        print("\nrings 2-4 gap table:")
        print(gap_table(load(a.reviewed), load(a.derived), json.loads(Path(a.snapshot).read_text()), a.prom))
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
