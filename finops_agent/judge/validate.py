"""Validate the judge's reply. Anything ungrounded is rejected and recorded, never repaired."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from finops_agent.judge.brief import Brief, ZERO
from finops_agent.judge.prompt import STEPS, TYPES

VERDICTS = ("waste", "not_waste", "insufficient_evidence")
PROTECTIVE_TAG_KEYS = ("dr", "keep", "do-not-delete", "retain")   # intent tags: idle by design
NUM = re.compile(r"(?<![\w.])\$?\d[\d,]*(?:\.\d+)?%?")
DATE = re.compile(r"\d{4}-\d{2}(-\d{2})?")


class Rejected(Exception):
    pass


@dataclass
class Judgment:
    verdict: str
    type: str = ""
    method_step: str = ""
    title: str = ""
    resources: list = None
    hops: list = None
    evidence: list = None
    savings_choice: str = ZERO
    basis: str = "none"
    reasoning: str = ""


def extract_json(text: str) -> dict:
    t = text.strip()
    if t.startswith('"') and t.endswith('"'):
        try:
            t = json.loads(t)
        except ValueError:
            pass
    t = re.sub(r"^```(?:json)?|```$", "", t.strip(), flags=re.M).strip()
    try:
        return json.loads(t)
    except ValueError:
        pass
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        raise Rejected("reply is not JSON")
    try:
        return json.loads(t[i:j + 1])
    except ValueError as e:
        raise Rejected(f"reply is not valid JSON: {e}")


def _evidence_numbers(b: Brief) -> list:
    nums = []
    texts = [e.what for e in b.facts] + [f"{c.value:.2f} {c.desc}" for c in b.candidates] + [b.signal]
    if b.resource_spend_usd is not None:
        texts.append(f"{b.resource_spend_usd:.2f}")
    for t in texts:
        for m in NUM.finditer(DATE.sub("", t)):
            nums.append(_num(m.group()))
    return nums


def _num(s: str) -> float:
    return float(s.strip("$%").replace(",", ""))


def ungrounded_numbers(text: str, b: Brief) -> list:
    """Numbers in free text that appear nowhere in the evidence. Small bare integers are exempt."""
    known = _evidence_numbers(b)
    bad = []
    for m in NUM.finditer(DATE.sub("", text)):
        raw = m.group()
        n = _num(raw)
        if n < 100 and not raw.startswith("$") and not raw.endswith("%"):
            continue
        cands = [n, n / 100] if raw.endswith("%") else [n]
        if not any(abs(c - k) <= max(0.01 * abs(k), 0.5 if k >= 100 else 0.006) or abs(c - k / 100) <= 0.006 for c in cands for k in known):
            bad.append(raw)
    return bad


def validate(raw: str, b: Brief, protected: set | None = None) -> Judgment:
    d = extract_json(raw)
    v = d.get("verdict")
    if v not in VERDICTS:
        raise Rejected(f"verdict {v!r} not in {VERDICTS}")
    texts = " ".join(str(d.get(k, "")) for k in ("title", "reasoning")) + " " + " ".join(map(str, d.get("hops") or []))
    bad = ungrounded_numbers(texts, b)
    if bad:
        raise Rejected(f"numbers not found in the evidence: {bad}")
    cited = d.get("evidence") or []
    ids = b.fact_ids()
    if not isinstance(cited, list) or any(c not in ids for c in cited):
        raise Rejected(f"evidence ids not in the brief: {cited}")
    j = Judgment(v, str(d.get("type", "")), str(d.get("method_step", "")), str(d.get("title", "")), list(d.get("resources") or []),
                 list(d.get("hops") or []), cited, str(d.get("savings_choice", ZERO)), str(d.get("basis", "none")), str(d.get("reasoning", "")))
    if not j.title or not j.reasoning:
        raise Rejected("title and reasoning are required")
    if v != "waste":
        return j
    if j.type not in TYPES:
        raise Rejected(f"type {j.type!r} not in the taxonomy")
    if j.method_step not in STEPS:
        raise Rejected(f"method_step {j.method_step!r} not in {STEPS}")
    if not j.resources or not set(j.resources) <= set(b.resources):
        raise Rejected(f"resources {j.resources} not within the allowed list")
    if len(j.hops) < 2 or not all(isinstance(h, str) and h for h in j.hops):
        raise Rejected("hops need at least 2 non-empty strings")
    if not cited:
        raise Rejected("a waste verdict must cite evidence")
    if j.savings_choice != ZERO:
        c = b.candidate(j.savings_choice)
        if c is None:
            raise Rejected(f"savings_choice {j.savings_choice!r} is not a computed candidate")
        if j.basis != c.basis:
            raise Rejected(f"basis {j.basis!r} does not match the candidate's basis {c.basis!r}")
    elif j.basis != "none":
        raise Rejected("savings_choice none requires basis none")
    hit = set(j.resources) & (protected or set())
    if hit:
        raise Rejected(f"{sorted(hit)} carry an intent tag ({'/'.join(PROTECTIVE_TAG_KEYS)}): idle by design")
    return j
