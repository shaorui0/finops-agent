"""Ring 1 by LLM: derive the visibility requirements from cost goals, goal-first (FA12).

The model sees the goals file and the output schema, and nothing else: no metric names from the metrics
server, none from config/visibility_requirements.yaml. Since c0020 it also does not guess metric names (c0017
showed that guessed regexes such as aws_ec2_network_in.* simply do not exist): it states each needed signal in
words (`concept`, `terms`) plus a scope. Ring 2 (visibility.discover) looks through the live server's metric
catalogue and finds the candidate names by meaning; rings 3-4 then check coverage.

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
PROMPT_VERSION = "v4"

INSTRUCTIONS = """You are designing the visibility requirements for an AWS cost-optimisation agent.
Below is a business description of one AWS account and its cost goals (written in Chinese).

Task: for every goal that can be measured by time-series signals, define the SLIs (service level indicators)
needed to measure it and to protect the cost decision behind it, and list the signals each SLI needs.
Work goal-first: reason only from the goals. You have not been shown the monitoring system and must not
assume what exists there; say what you would need, not what you think is available.

Describe every needed signal in words. Do NOT write metric names, name patterns or regular expressions:
a later step looks through the real monitoring system and finds the matching metrics by meaning, using
your words. Per need give:
  signal   what is measured, one Chinese phrase
  concept  the same quantity as one short English phrase: the physical quantity, per what, in which unit
           (for example "memory utilisation percent per instance")
  terms    5 to 8 lowercase English words that a metric name or its help text for this quantity is likely to
           contain: the core nouns plus common synonyms and unit words. Single plain words only (a-z, 0-9),
           no underscores, no punctuation, no prefixes of any particular exporter.
Choose the terms so that they pick out this quantity and not its neighbours: if the need is latency, do not
list generic words such as "total" or "seconds" alone.

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
           "need": [{"signal": "<Chinese phrase>", "concept": "<English phrase>", "terms": ["word", "word"],
                     "scope": "<allowed scope>"}]}],
 "not_metric_observable": [{"goal": "G5", "reason": "<one line, Chinese>"}]}
If a goal names several separate things (for example two different traffic paths), each of them needs its
own signal. Keep SLIs distinct and minimal: one SLI per cost decision, 1-3 needs each. Every metric goal must be
covered by at least one SLI.

=== ACCOUNT AND COST GOALS ===
"""


def build_prompt(goals_text: str, sample: int | None = None) -> str:
    """`sample` only makes the prompt (and so the cassette key) unique per draw; it does not change the task."""
    tail = f"\n(draw #{sample})\n" if sample else "\n"
    return INSTRUCTIONS + goals_text.strip() + tail


def extract_json(text: str) -> dict:
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        i, j = t.find("{"), t.rfind("}")
        if i < 0 or j <= i:
            raise ValueError("no JSON object in model output")
        return json.loads(t[i:j + 1])


TERM_RE = re.compile(r"^[a-z0-9]+$")
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
            if "name" in n:
                errs.append(f"{sid}: need carries a metric `name`; ring 1 states words only (FA12), ring 2 discovers names")
            terms = n.get("terms")
            if not isinstance(terms, list) or not 3 <= len(terms) <= 12 or not all(TERM_RE.match(str(t)) for t in terms):
                errs.append(f"{sid}: `terms` must be 3-12 plain lowercase words, got {terms!r}")
            if not n.get("concept"):
                errs.append(f"{sid}: need without concept")
            if not n.get("signal"):
                errs.append(f"{sid}: need without signal")
    return errs


HEADER = ("# 第 ① 环，由 LLM 从 config/cost_goals.yaml 推出（未查看任何现有指标）。\n"
          "# 由 `python3 -m finops_agent.visibility_llm derive` 生成，格式同 visibility_requirements.yaml。\n")


def derive(goals_path: Path, out_path: Path, client: LLMClient | None = None, sample: int | None = 1) -> dict:
    client = client or LLMClient()
    r = client.complete(build_prompt(Path(goals_path).read_text(), sample))
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
    p.add_argument("--sample", type=int, default=1, help="draw number; each draw has its own cassette")
    a = ap.parse_args(argv)
    d = derive(Path(a.goals), Path(a.out), sample=a.sample)
    c = d["_call"]
    print(f"{len(d['slis'])} SLIs, {sum(len(s['need']) for s in d['slis'])} needs -> {a.out}  "
          f"[{c['mode']} {c['model']} tokens {c['tokens_in']}/{c['tokens_out']} ${c['cost_usd']:.4f} key {c['key'][:12]}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
