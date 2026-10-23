"""finops-agent CLI.

  python3 -m finops_agent run --aws-endpoint http://127.0.0.1:4566 --prom http://127.0.0.1:9090
  python3 -m finops_agent run --snapshot runs/<id>/snapshot.json    # re-analyze a frozen snapshot

Writes runs/<run_id>/{snapshot.json, visibility.json, findings.json, slo.json, finops_metrics.prom,
trace.jsonl, report.html} and updates runs/state.json (cross-run state for rot detection).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from finops_agent.analyze import Analyzer, check_invariants
from finops_agent.collect import Collector, Config, Trace, save
from finops_agent import report, slo, visibility

ROOT = Path(__file__).resolve().parent.parent


def run(args) -> Path:
    cfg = Config(aws_endpoint=args.aws_endpoint, prom_url=args.prom, region=args.region,
                 start=date.fromisoformat(args.start), end=date.fromisoformat(args.end))
    trace = Trace()
    col = Collector(cfg, trace)
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(args.out) / run_id

    snap = json.loads(Path(args.snapshot).read_text()) if args.snapshot else col.snapshot()
    save(snap, out / "snapshot.json")

    reqs = visibility.ring1(ROOT / "config" / "visibility_requirements.yaml")
    plan = visibility.ring2(reqs, snap)
    results = visibility.ring3(plan, col)
    gaps = visibility.ring4(reqs, plan, results)
    save({"requirements": reqs, "plan": plan, "search": results, "gaps": gaps}, out / "visibility.json")

    a = Analyzer(snap, cfg.days).run()
    inv = check_invariants(a.findings)
    findings = [f.to_dict() for f in a.findings]
    result = {"run_id": run_id, "account": snap["identity"]["Account"], "period": snap["period"],
              "findings": findings, "leads": [l.to_dict() for l in a.leads], "ranking": a.ranking,
              "attribution": a.attribution_summary, "invariants": inv,
              "visibility": {"gaps": gaps}, "trace": trace.calls}
    state_path = Path(args.state)
    prev = slo.load_state(state_path)
    slis = slo.compute_slis(result, snap, col, cfg.end, prev)
    rows = slo.evaluate(slis, slo.load_cfg(ROOT / "config" / "finops_slo.yaml"))
    diff, new_state = slo.diff_state(findings, prev, run_id, cfg.end)
    result["slo"] = {"rows": rows, "diff": diff, "previous_runs": len((prev or {}).get("runs", []))}
    save(result["slo"], out / "slo.json")
    (out / "finops_metrics.prom").write_text(slo.to_prometheus(rows, diff, run_id, datetime.now(timezone.utc).timestamp()))
    if not args.no_state:
        save(new_state, state_path)
    save({k: v for k, v in result.items() if k != "trace"}, out / "findings.json")
    (out / "trace.jsonl").write_text("".join(json.dumps(c, default=str) + "\n" for c in trace.calls))
    (out / "report.html").write_text(report.render(result))
    print(f"run {run_id}: {len(findings)} findings, {len(a.leads)} leads, invariants {'pass' if not inv else inv}", file=sys.stderr)
    print(out / "report.html")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="finops_agent")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="collect, analyze, report")
    r.add_argument("--aws-endpoint", default=None, help="test-aws-server URL; omit for real AWS")
    r.add_argument("--prom", default="http://127.0.0.1:9090")
    r.add_argument("--region", default="us-east-1")
    r.add_argument("--start", default="2026-09-01")
    r.add_argument("--end", default="2026-10-01")
    r.add_argument("--out", default=str(ROOT / "runs"))
    r.add_argument("--run-id", default=None)
    r.add_argument("--snapshot", default=None, help="analyze an existing snapshot instead of collecting")
    r.add_argument("--state", default=str(ROOT / "runs" / "state.json"), help="cross-run state for rot detection")
    r.add_argument("--no-state", action="store_true", help="do not update the cross-run state")
    args = ap.parse_args(argv)
    if args.cmd == "run":
        run(args)


if __name__ == "__main__":
    main()
