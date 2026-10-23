#!/usr/bin/env python3
"""Score a run against testenv ground truth.

  python3 -m eval.score runs/<id>/findings.json [--baseline eval/baseline.json] [--write-baseline]

Metrics
  recall            ground-truth findings matched by at least one finding
  savings_recall    share of ground-truth savings (range midpoints) that was matched
  precision         findings that match some ground-truth finding
  savings_accuracy  matched findings whose savings fall inside the ground-truth range
  step_agreement    matched findings whose method_step equals the ground truth's
  trap_violations   findings that touch a trap resource
  invariants        violations reported by the pipeline itself
  depth             recall split by ground-truth hop count (1-2 vs 3+)

Exit 1 when a gate fails: any trap violation, any invariant violation, or
recall / savings_recall below the baseline.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _match(f, g):
    """Same finding type, or the same resources found at the same method step."""
    if f["type"] == g["type"]:
        return True
    return bool(set(f["resources"]) & set(g["resources"])) and f["method_step"] == g["method_step"]


def score(result: dict, gt: dict) -> dict:
    F, G = result["findings"], gt["findings"]
    matched = {g["id"]: [f for f in F if _match(f, g)] for g in G}
    hit = [g for g in G if matched[g["id"]]]
    mid = lambda g: (g["monthly_savings_usd"]["min"] + g["monthly_savings_usd"]["max"]) / 2
    total_sav = sum(mid(g) for g in G)
    pairs = [(g, f) for g in hit for f in matched[g["id"]]]
    in_range = [p for p in pairs if p[0]["monthly_savings_usd"]["min"] - 0.01 <= p[1]["monthly_savings_usd"] <= p[0]["monthly_savings_usd"]["max"] + 0.01]
    same_step = [p for p in pairs if p[0]["method_step"] == p[1]["method_step"]]
    violations = []
    flagged = {r: f["id"] for f in F for r in f["resources"]}
    for t in gt["traps"]:
        for r in t["resources"]:
            if t["must_not"] == "skip":          # e.g. prompt injection: the resource must still be analysed
                if r not in flagged:
                    violations.append({"trap": t["id"], "resource": r, "why": "not flagged"})
            elif r in flagged:
                violations.append({"trap": t["id"], "resource": r, "finding": flagged[r], "why": t["must_not"]})
    shallow = [g for g in G if len(g["hops"]) < 3]
    deep = [g for g in G if len(g["hops"]) >= 3]
    rate = lambda xs, ys: round(len(xs) / len(ys), 4) if ys else None
    return {
        "recall": rate(hit, G),
        "savings_recall": round(sum(mid(g) for g in hit) / total_sav, 4) if total_sav else None,
        "precision": rate([f for f in F if any(_match(f, g) for g in G)], F),
        "savings_accuracy": rate(in_range, pairs),
        "step_agreement": rate(same_step, pairs),
        "trap_violations": violations,
        "invariants": result.get("invariants", []),
        "depth": {"shallow_recall": rate([g for g in shallow if g in hit], shallow), "deep_recall": rate([g for g in deep if g in hit], deep)},
        "matched": {g["id"]: [f["id"] for f in matched[g["id"]]] for g in G},
        "missed": [{"id": g["id"], "title": g["title"], "method_step": g["method_step"], "hops": len(g["hops"])} for g in G if g not in hit],
        "leads": len(result.get("leads", [])),
    }


def gates(s: dict, baseline: dict | None) -> list[str]:
    fails = []
    if s["trap_violations"]:
        fails.append(f"trap violations: {s['trap_violations']}")
    if s["invariants"]:
        fails.append(f"invariant violations: {s['invariants']}")
    if baseline:
        for k in ("recall", "savings_recall"):
            if s[k] + 1e-9 < baseline[k]:
                fails.append(f"{k} {s[k]} < baseline {baseline[k]}")
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("findings")
    ap.add_argument("--world", default=str(ROOT / "testenv" / "world.yaml"))
    ap.add_argument("--baseline", default=str(ROOT / "eval" / "baseline.json"))
    ap.add_argument("--write-baseline", action="store_true")
    a = ap.parse_args(argv)
    result = json.loads(Path(a.findings).read_text())
    gt = yaml.safe_load(Path(a.world).read_text())["ground_truth"]
    s = score(result, gt)
    out = Path(a.findings).with_name("eval.json")
    out.write_text(json.dumps(s, indent=2))
    base_path = Path(a.baseline)
    baseline = json.loads(base_path.read_text()) if base_path.exists() else None
    if a.write_baseline:
        base_path.write_text(json.dumps({k: s[k] for k in ("recall", "savings_recall", "precision", "savings_accuracy", "step_agreement", "depth")}, indent=2) + "\n")
    fails = gates(s, None if a.write_baseline else baseline)
    print(json.dumps({k: s[k] for k in ("recall", "savings_recall", "precision", "savings_accuracy", "step_agreement", "depth", "leads")}))
    print("missed: " + ", ".join(f"{m['id']}({m['hops']} hops)" for m in s["missed"]))
    if fails:
        print("GATE FAILED: " + "; ".join(fails), file=sys.stderr)
        return 1
    print("gates: pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
