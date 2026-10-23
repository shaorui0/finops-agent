"""Ring 1 by LLM: derive the visibility requirements from cost goals, goal-first (FA12).

The model sees the goals file and the output schema, and nothing else: no metric names from the metrics
server, none from config/visibility_requirements.yaml. It has to guess metric-name patterns from general
knowledge of Prometheus / CloudWatch-exporter conventions, which is exactly what a ring-1 author does
before looking at the system. Rings 2-4 then find out how good the guesses were.

    python3 -m finops_agent.visibility_llm derive --goals config/cost_goals.yaml --out runs/ring1_llm.yaml

Mode comes from FINOPS_LLM_MODE (replay by default, see finops_agent/llm.py).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

from finops_agent.llm import LLMClient

ROOT = Path(__file__).resolve().parent.parent
PROMPT_VERSION = "v3"

INSTRUCTIONS = """You are designing the visibility requirements for an AWS cost-optimisation agent.
Below is a business description of one AWS account and its cost goals (written in Chinese).

Task: for every goal that can be measured by time-series signals, define the SLIs (service level indicators)
needed to measure it and to protect the cost decision behind it, and list the signals each SLI needs.
Work goal-first: reason only from the goals. You have not been shown the monitoring system and must not
assume what exists there; say what you would need, not what you think is available.

The monitoring system is Prometheus-style. For every needed signal give `name`: a regular expression over
Prometheus metric names (full match), written from your general knowledge of common exporters, for example
the CloudWatch exporter prefix `aws_<service>_<metric>` or application counters/histograms. Prefer a
precise pattern, but end it with `.*` where the unit or statistic suffix (for example `_sum` or `_total`)
is genuinely unknowable. Different exporters use different suffixes.

Every need has a `scope`: which resources must be covered for the SLI to be computable. Allowed values only:
  running_instances        every running EC2 instance
  nat_gateways             every NAT gateway
  services:<a>,<b>         the listed services, by service name from the account description (comma list, no spaces)
Scope meaning: `running_instances` and `nat_gateways` are for infrastructure metrics keyed by instance or
gateway. `services:` is for application-level metrics that the services themselves report, keyed by service.
Use the one that matches where the signal is produced.

Goals that are measured from the AWS API, billing data or resource tags rather than from time series
(for example commitment utilisation, tag-based ownership, orphan resource age) go in `not_metric_observable`,
each with a one-line reason. Do not invent a time-series signal for them.

Output exactly one JSON object, no prose, in this shape:
{"slis": [{"id": "snake_case_id", "decision": "<cost decision this SLI protects, one sentence, Chinese>",
           "goals": ["G1"],
           "need": [{"signal": "<what is measured, Chinese>", "name": "<regex>", "scope": "<allowed scope>"}]}],
 "not_metric_observable": [{"goal": "G5", "reason": "<one line, Chinese>"}]}
If a goal names several separate things (for example two different traffic paths), each of them needs its
own signal. Keep SLIs distinct and minimal: one SLI per cost decision, 1-3 needs each. Every metric goal must be
covered by at least one SLI.

=== ACCOUNT AND COST GOALS ===
"""


def build_prompt(goals_text: str) -> str:
    return INSTRUCTIONS + goals_text.strip() + "\n"


def extract_json(text: str) -> dict:
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        i, j = t.find("{"), t.rfind("}")
        if i < 0 or j <= i:
            raise ValueError("no JSON object in model output")
        return json.loads(t[i:j + 1])


SCOPE_RE = re.compile(r"^(running_instances|nat_gateways|services:[A-Za-z0-9_-]+(,[A-Za-z0-9_-]+)*)$")


def validate(d: dict) -> list[str]:
    """Return a list of problems; empty means the ring-1 document is usable by rings 2-4."""
    errs = []
    slis = d.get("slis")
    if not isinstance(slis, list) or not slis:
        return ["`slis` missing or empty"]
    seen = set()
    for s in slis:
        sid = s.get("id", "?")
        if sid in seen:
            errs.append(f"duplicate sli id {sid}")
        seen.add(sid)
        if not s.get("decision"):
            errs.append(f"{sid}: no decision")
        if not s.get("need"):
            errs.append(f"{sid}: no need")
        for n in s.get("need", []):
            if not SCOPE_RE.match(str(n.get("scope", ""))):
                errs.append(f"{sid}: bad scope {n.get('scope')!r}")
            try:
                re.compile(str(n.get("name", "")))
            except re.error as e:
                errs.append(f"{sid}: bad regex {n.get('name')!r}: {e}")
            if not n.get("signal"):
                errs.append(f"{sid}: need without signal")
    return errs


HEADER = ("# 第 ① 环，由 LLM 从 config/cost_goals.yaml 推出（未查看任何现有指标）。\n"
          "# 由 `python3 -m finops_agent.visibility_llm derive` 生成，格式同 visibility_requirements.yaml。\n")


def derive(goals_path: Path, out_path: Path, client: LLMClient | None = None) -> dict:
    client = client or LLMClient()
    r = client.complete(build_prompt(Path(goals_path).read_text()))
    d = extract_json(r.text)
    errs = validate(d)
    if errs:
        raise ValueError("derived ring 1 is invalid: " + "; ".join(errs))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(HEADER + yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=140))
    d["_call"] = {"tokens_in": r.tokens_in, "tokens_out": r.tokens_out, "cost_usd": r.cost_usd, "mode": r.mode,
                  "key": r.key, "model": r.model}
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="finops_agent.visibility_llm")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("derive", help="derive ring 1 from a goals file with the LLM")
    p.add_argument("--goals", default=str(ROOT / "config" / "cost_goals.yaml"))
    p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    d = derive(Path(a.goals), Path(a.out))
    c = d["_call"]
    print(f"{len(d['slis'])} SLIs, {sum(len(s['need']) for s in d['slis'])} needs -> {a.out}  "
          f"[{c['mode']} {c['model']} tokens {c['tokens_in']}/{c['tokens_out']} ${c['cost_usd']:.4f} key {c['key'][:12]}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
