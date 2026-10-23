#!/usr/bin/env python3
"""Run the full agent on a world and score it; report in-sample and held-out results separately.

  python3 -m eval.heldout                       # base world (in-sample) + next_month + month_after (held-out)
  python3 -m eval.heldout --json out.json       # also write every number as JSON
  FINOPS_LLM_MODE=record python3 -m eval.heldout   # record the cassettes the held-out worlds need (the only live LLM use)

In-sample = testenv/world.yaml. The judge prompt's rubric was iterated against exactly this account (c0009), so its
numbers are an upper bound. Held-out = the two scenario overlays next_month and month_after: same agent, same prompt, a
different month of the same synthetic account. The prompt is never edited in response to held-out numbers.

Held-out ground truth is derived from each scenario's own `scenario.expect` (resolved / new / regressed, with the `gt`
ids in `details`) applied to the base ground truth entries; nothing is read to tune the agent.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
import threading
from datetime import date
from argparse import Namespace
from http.server import ThreadingHTTPServer
from pathlib import Path

import yaml

from eval.score import gates, score
from testenv import aws_server, metrics_server, world as world_mod

ROOT = Path(__file__).resolve().parent.parent
SCEN = ROOT / "testenv" / "scenarios"
PORT_RANGE = range(31568, 31600)     # in-process test servers bind here
KEYS = ("recall", "savings_recall", "precision", "savings_accuracy", "step_agreement", "depth", "leads")
PRICE = {"gp2": 0.10, "gp3": 0.08, "io1": 0.125}


def _serve(handler):
    for port in PORT_RANGE:
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), handler)
        except OSError:
            continue
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv, f"http://127.0.0.1:{port}"
    raise RuntimeError(f"no free port in {PORT_RANGE.start}-{PORT_RANGE.stop - 1}")


def run_world(path, run_id: str = "w", out: str | None = None) -> dict:
    """Run the whole agent (judge uses FINOPS_LLM_MODE, default replay) against the world file `path` (None = base).

    Scenario files may carry `scenario.job_labels: {profile: label}`: the test metrics server hard-codes the job label per
    profile, so this is applied here to the in-process server only (a Prometheus label-value carrier for adversarial tests).
    """
    from finops_agent.__main__ import run
    tmp = tempfile.TemporaryDirectory() if out is None else None
    outdir = out or tmp.name
    world_mod.use(path)
    saved = dict(world_mod.JOB_BY_PROFILE)
    try:
        w = world_mod.load()
        world_mod.JOB_BY_PROFILE.update(w.raw.get("scenario", {}).get("job_labels", {}))
        aws, aws_url = _serve(aws_server.Handler)
        prom, prom_url = _serve(metrics_server.Handler)
        try:
            s, e = w.period
            d = run(Namespace(aws_endpoint=aws_url, prom=prom_url, region="us-east-1", start=s.isoformat(), end=e.isoformat(),
                              out=outdir, run_id=run_id, snapshot=None, state=f"{outdir}/state.json", no_state=True))
            result = json.loads((d / "findings.json").read_text())
            result["trace"] = [json.loads(l) for l in (d / "trace.jsonl").read_text().splitlines()]
            return result
        finally:
            aws.shutdown(); prom.shutdown(); aws.server_close(); prom.server_close()
    finally:
        world_mod.JOB_BY_PROFILE.clear(); world_mod.JOB_BY_PROFILE.update(saved)
        world_mod.use(None)
        if tmp:
            tmp.cleanup()


# ---- ground truth ---------------------------------------------------------------------------
def base_ground_truth() -> dict:
    return yaml.safe_load((ROOT / "testenv" / "world.yaml").read_text())["ground_truth"]


def _scenario_chain(path: Path) -> list:
    """[(file, scenario dict)] from the oldest overlay to `path`."""
    sc = yaml.safe_load(path.read_text())["scenario"]
    base = (path.parent / sc["base"]).resolve()
    prev = _scenario_chain(base) if base.name != "world.yaml" else []
    return prev + [(path, sc)]


def expected_ground_truth(path: Path) -> dict:
    """Base ground truth with each scenario's expect applied in order.

    resolved: drop the ground-truth entry named by `details[key].gt` (the entry for that key's resources).
    new / regressed: add the entry named by `gt`; for a new key whose resources differ from the base entry, the entry is cloned
    onto the new resources and its savings range is recomputed from the scenario world's own volume size and price (+-5%).
    """
    gt = copy.deepcopy(base_ground_truth())
    base_entries = {g["id"]: g for g in gt["findings"]}
    alive = {g["id"]: g for g in gt["findings"]}      # slot -> entry
    for file, sc in _scenario_chain(path):
        raw = world_mod.read_world(file)
        exp = sc["expect"]
        det = exp.get("details", {})
        for key in exp.get("resolved", []):
            rid = key.split("|", 1)[1]
            slot = next((s for s, g in alive.items() if set(rid.split(",")) & set(g["resources"])), None)
            if slot:
                del alive[slot]
        for key in exp.get("new", []) + exp.get("regressed", []):
            gid = det[key]["gt"]
            ent = copy.deepcopy(base_entries[gid])
            res = key.split("|", 1)[1].split(",")
            if not set(res) & set(ent["resources"]):
                ent["resources"] = res
                vol = next((v for v in raw["volumes"] if v["id"] in res), None)
                if vol:
                    mid = vol["size"] * PRICE[vol["type"]]
                    ent["monthly_savings_usd"] = {"min": round(mid * 0.95, 2), "max": round(mid * 1.05, 2)}
            alive[f"{gid}:{key.split('|', 1)[1]}"] = ent
    gt["findings"] = list(alive.values())
    return gt


def scaled(gt: dict, days: int) -> dict:
    """Same ground truth with savings ranges multiplied by days/30 (the base ranges are for a 30-day month)."""
    g = copy.deepcopy(gt)
    for f in g["findings"]:
        f["monthly_savings_usd"] = {k: round(v * days / 30, 2) for k, v in f["monthly_savings_usd"].items()}
    return g


def evaluate(result: dict, gt: dict, days: int = 30) -> dict:
    s = score(result, gt)
    s["savings_accuracy_day_scaled"] = score(result, scaled(gt, days))["savings_accuracy"]
    s["judged"] = [{"lead": j["lead"], "kind": j["kind"], "verdict": j["verdict"], "accepted": j["accepted"], "reject_reason": j["reject_reason"]}
                   for j in result.get("judgments", [])]
    llm = [c for c in result.get("trace", []) if c.get("source") == "llm"]
    s["llm"] = {"calls": len(llm), "tokens_in": sum(c["tokens_in"] for c in llm), "tokens_out": sum(c["tokens_out"] for c in llm),
                "cost_usd": round(sum(c["cost_usd"] for c in llm), 4)}
    s["findings_n"] = len(result["findings"])
    s["gt_n"] = len(gt["findings"])
    s["gate_failures"] = gates(s, None)
    return s


WORLDS = [("base (in-sample)", None, "in-sample"), ("next_month", SCEN / "next_month.yaml", "held-out"), ("month_after", SCEN / "month_after.yaml", "held-out")]


def run_all(only=None) -> dict:
    out = {}
    for name, path, kind in WORLDS:
        if only and name not in only:
            continue
        result = run_world(path, run_id=name.split()[0])
        gt = base_ground_truth() if path is None else expected_ground_truth(path)
        days = (date.fromisoformat(result["period"]["End"]) - date.fromisoformat(result["period"]["Start"])).days
        out[name] = {"kind": kind, "days": days, **evaluate(result, gt, days), "findings": [(f["type"], f["method_step"], f["resources"]) for f in result["findings"]]}
    return out


def table(res: dict) -> str:
    cols = ["recall", "savings_recall", "precision", "savings_accuracy", "savings_accuracy_day_scaled", "step_agreement"]
    lines = ["| world | kind | " + " | ".join(cols) + " | traps | invariants | findings/GT | LLM calls | cost |", "|" + "---|" * (len(cols) + 7)]
    for name, r in res.items():
        lines.append(f"| {name} | {r['kind']} | " + " | ".join(str(r[c]) for c in cols) +
                     f" | {len(r['trap_violations'])} | {len(r['invariants'])} | {r['findings_n']}/{r['gt_n']} | {r['llm']['calls']} | ${r['llm']['cost_usd']:.4f} |")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write all numbers as JSON")
    ap.add_argument("--only", nargs="*", help="world names to run")
    a = ap.parse_args(argv)
    res = run_all(a.only)
    print(table(res))
    for name, r in res.items():
        print(f"\n[{name}] missed: {[(m['id'], m['title']) for m in r['missed']] or 'none'}; depth={r['depth']}")
        print(f"[{name}] judged: " + "; ".join(f"{j['lead']}:{j['kind']}={j['verdict']}{'' if j['accepted'] else ' REJECTED(' + str(j['reject_reason']) + ')'}" for j in r["judged"]))
        if r["trap_violations"]:
            print(f"[{name}] trap violations: {r['trap_violations']}")
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
