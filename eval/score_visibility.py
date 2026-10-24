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
  Since c0020 a derived need states words (`terms`), not a regex. It is resolved to metric names by ring 2's
  deterministic `visibility.discover` against the same universe (server catalogue incl. HELP text, plus the
  PROBE names without HELP), then compared with the reviewed need's names exactly as above. A derived need
  that still carries a `name` regex (c0017 files) is scored the old way.
  recall     reviewed needs covered / reviewed needs                     (the "overlap", target >= 0.8)
  precision  derived needs that cover some reviewed need / derived needs
  name-only  recall with the scope condition dropped (how much is lost to scope vocabulary alone)
  SLI level  a reviewed SLI is covered if all its needs are covered, partial if some
There is deliberately no semantic "same decision class" fallback: it needs a judge, and a judge would make
the score depend on a second model.

    python3 -m eval.score_visibility --derived runs/ring1_llm.yaml [--prom http://127.0.0.1:33566]
    python3 -m eval.score_visibility --samples 5 [--outdir DIR]   # derive N times, report mean/min/max overlap
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


def server_catalog(prom: str | None = None) -> dict[str, dict]:
    """Metric catalogue (name -> help, type, labels) of the test metrics server, over HTTP or in-process."""
    if prom:
        from finops_agent.collect import Collector, Config, Trace
        from finops_agent import visibility
        return visibility.fetch_catalog(Collector(Config(aws_endpoint=None, prom_url=prom), Trace()))
    from testenv import metrics_server
    cat = {n: {"help": h, "type": t, "labels": set()} for n, (t, h) in metrics_server.METADATA.items()}
    for x in metrics_server.build()[1]:
        cat.setdefault(x.labels["__name__"], {"help": "", "type": "", "labels": set()})["labels"].update(
            k for k in x.labels if k != "__name__")
    return cat


def universe_catalog(catalog: dict[str, dict]) -> dict[str, dict]:
    """Server catalogue plus the probe names (no HELP, no labels), so planted gaps can be compared."""
    out = dict(catalog)
    for p in PROBES:
        out.setdefault(p, {"help": "", "type": "", "labels": set()})
    return out


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


def need_names(need: dict, universe: set[str], catalog: dict[str, dict]) -> set[str]:
    """Metric names a need stands for in the universe: its regex, or ring-2 discovery for a words-only need."""
    if "name" in need:
        d = matches(need["name"], universe)
    else:
        from finops_agent import visibility
        label = visibility.SCOPE_LABEL.get(need["scope"], "job" if need["scope"].startswith("services:") else "")
        d = {c["name"] for c in visibility.discover(need, label, catalog)}
    return set() if len(d) > WILDCARD_SHARE * len(universe) else d


def score(reviewed: list[dict], derived: list[dict], names: set[str], catalog: dict | None = None) -> dict:
    universe = set(names) | set(PROBES)
    catalog = universe_catalog(catalog if catalog is not None else {n: {"help": "", "type": "", "labels": set()} for n in names})
    dneeds = [(s["id"], n) for s in derived for n in s["need"]]
    dres = [need_names(d, universe, catalog) for _, d in dneeds]
    rows, total, hit, hit_name = [], 0, 0, 0
    used = set()
    for s in reviewed:
        cov = []
        for n in s["need"]:
            by = [(sid, i) for i, (sid, d) in enumerate(dneeds)
                  if scope_overlap(n["scope"], d["scope"]) and matches(n["name"], universe) & dres[i]]
            by_name = [1 for i, (sid, d) in enumerate(dneeds) if matches(n["name"], universe) & dres[i]]
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
        real = dres[i] & set(names)
        extra.append({"sli": sid, "name": d.get("name") or d.get("concept", "?"), "scope": d["scope"], "real_metrics": sorted(real),
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


def run_rings(slis: list[dict], snap: dict, prom: str, mix: bool = False) -> dict:
    """Rings 2-4 (finops_agent.visibility) for one ring-1 list against the live test metrics server.
    Needs without a `name` are discovered in ring 2 from the server's catalogue."""
    from finops_agent import visibility
    from finops_agent.collect import Collector, Config, Trace
    col = Collector(Config(aws_endpoint=None, prom_url=prom), Trace())
    catalog = visibility.fetch_catalog(col) if any("name" not in n for s in slis for n in s["need"]) else None
    plan = visibility.ring2(slis, snap, catalog)
    return {g["sli"]: {**g, "plan": [p for p in plan if p["sli"] == g["sli"]]}
            for g in visibility.ring4(slis, plan, visibility.ring3(plan, col), mix=mix)}


def gap_table(reviewed: list[dict], derived: list[dict], snap: dict, prom: str) -> str:
    """Gap table of the reviewed ring 1 next to the derived one (derived after ring-2 discovery, ring-4 need-level mix).
    Derived SLIs are shown under the reviewed SLI that shares a need with them (strict rule above); the rest are
    listed as derived-only. A derived SLI shows its status and its mix as covered/partial/missing needs."""
    rg, dg = run_rings(reviewed, snap, prom), run_rings(derived, snap, prom, mix=True)
    cat = universe_catalog(server_catalog(prom))
    names = set(cat)
    resolved = {d["id"]: [(m, need_names(m, names, cat)) for m in d["need"]] for d in derived}
    fmt = lambda d: f"{d} ({dg[d]['status']} {dg[d]['mix']['covered']}/{dg[d]['mix']['partial']}/{dg[d]['mix']['missing']})"
    out = [f"{'ring-4 status':<14}{'reviewed SLI':<24}{'derived SLI (status c/p/m needs)':<62}"]
    claimed = set()
    for s in reviewed:
        ds = [d["id"] for d in derived if any(scope_overlap(n["scope"], m["scope"]) and matches(n["name"], names) & r
                                              for n in s["need"] for m, r in resolved[d["id"]])]
        claimed.update(ds)
        out.append(f"{rg[s['id']]['status']:<14}{s['id']:<24}{', '.join(fmt(d) for d in ds) or '-'}")
    only = [d["id"] for d in derived if d["id"] not in claimed]
    out += ["", "derived-only SLIs: " + (", ".join(fmt(d) for d in only) or "(none)")]
    cnt = lambda g: {k: sum(v["status"] == k for v in g.values()) for k in ("covered", "partial", "missing")}
    out += [f"reviewed ring-4 totals: {cnt(rg)}", f"derived  ring-4 totals: {cnt(dg)}", "",
            "ring-2 discovery per derived need (candidate metric names found by meaning):"]
    for d in derived:
        for n, p in zip(d["need"], dg[d["id"]]["plan"]):
            out.append(f"  {d['id']}: {n['concept']} [{n['scope']}] -> "
                       + (", ".join(c["name"] for c in p["discovered"]) or "(no candidate)"))
    return "\n".join(out)


def load(path) -> list[dict]:
    return yaml.safe_load(Path(path).read_text())["slis"]


def samples(n: int, goals: Path, outdir: Path, reviewed: list[dict], names: set[str], catalog: dict) -> list[dict]:
    """Derive ring 1 n times (draws 1..n; record mode makes n real LLM calls) and score each draw."""
    from finops_agent.visibility_llm import derive
    outdir.mkdir(parents=True, exist_ok=True)
    out = []
    for k in range(1, n + 1):
        path = outdir / f"ring1_sample{k}.yaml"
        d = derive(goals, path, sample=k)
        r = score(reviewed, load(path), names, catalog)
        out.append({"sample": k, "path": str(path), "recall": r["recall"], "precision": r["precision"],
                    "covered": r["covered_needs"], "of": r["reviewed_needs"], "result": r, "call": d["_call"]})
    return out


def render_samples(res: list[dict]) -> str:
    rec = [r["recall"] for r in res]
    mean = sum(rec) / len(rec)
    out = [f"{'sample':<8}{'overlap':<16}{'precision':<11}{'cost_usd':<10}missed reviewed needs"]
    for r in res:
        miss = [n["name"] for row in r["result"]["rows"] for n in row["needs"] if not n["covered"]]
        out.append(f"{r['sample']:<8}{r['covered']}/{r['of']} = {r['recall']:<7.2f}{r['precision']:<11.2f}"
                   f"{r['call']['cost_usd']:<10.4f}{', '.join(miss) or '-'}")
    out += ["", f"overlap over {len(res)} samples: mean {mean:.3f}  min {min(rec):.2f}  max {max(rec):.2f}   (target: mean >= 0.80)",
            f"precision mean {sum(r['precision'] for r in res) / len(res):.3f}",
            f"verdict: {'MET' if mean >= 0.8 else 'NOT MET'} (mean {mean:.3f})"]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="eval.score_visibility")
    ap.add_argument("--derived", help="derived ring-1 yaml (single-file mode)")
    ap.add_argument("--samples", type=int, default=0, help="derive ring 1 N times and report mean/min/max overlap")
    ap.add_argument("--goals", default=str(ROOT / "config" / "cost_goals.yaml"))
    ap.add_argument("--outdir", default=str(ROOT / "runs" / "ring1_samples"))
    ap.add_argument("--reviewed", default=str(REVIEWED))
    ap.add_argument("--prom", default=None, help="metrics server URL; default: in-process testenv")
    ap.add_argument("--snapshot", default=None, help="snapshot.json from a run; with --prom, also run rings 2-4")
    ap.add_argument("--json", default=None, help="also write the full result here")
    a = ap.parse_args(argv)
    if not a.derived and not a.samples:
        ap.error("give --derived FILE or --samples N")
    names, catalog = server_metric_names(a.prom), server_catalog(a.prom)
    reviewed = load(a.reviewed)
    if a.samples:
        res = samples(a.samples, Path(a.goals), Path(a.outdir), reviewed, names, catalog)
        print(render_samples(res))
        if a.snapshot and a.prom:
            med = sorted(res, key=lambda r: r["recall"])[len(res) // 2]
            print(f"\nrings 2-4 gap table (median sample {med['sample']}):")
            print(gap_table(reviewed, load(med["path"]), json.loads(Path(a.snapshot).read_text()), a.prom))
        if a.json:
            Path(a.json).write_text(json.dumps([{k: v for k, v in r.items() if k != "result"} for r in res], indent=2))
        return 0
    res = score(reviewed, load(a.derived), names, catalog)
    print(render(res))
    if a.snapshot and a.prom:
        print("\nrings 2-4 gap table:")
        print(gap_table(reviewed, load(a.derived), json.loads(Path(a.snapshot).read_text()), a.prom))
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
