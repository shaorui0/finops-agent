"""Validate the judge's reply. Anything ungrounded is rejected and recorded, never repaired."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from finops_agent.judge.brief import Brief, ZERO
from finops_agent.judge.prompt import STEPS, TYPES

VERDICTS = ("waste", "not_waste", "insufficient_evidence")
PROTECTIVE_TAG_KEYS = ("dr", "keep", "do-not-delete", "retain")   # intent tags: idle by design
# Numeric grounding rules (every number in title / hops / reasoning must come from the lead's evidence):
#   G1  tokens: a number is `[$]digits[,digits][.digits][%]`. It must not be glued to ASCII letters, digits or a dot on its left
#       (so ids such as vol-0abc..., m5.2xlarge, p95, us-east-1a are not numbers), but it MAY follow a CJK character:
#       "省了1500元" has the number 1500. (The first version used \w and silently skipped numbers glued to Chinese text.)
#   G2  dates and clock times (2026-09-04, 09-04, 02:00) are removed first; they are facts about the calendar, not amounts.
#   G3  identifier-like tokens (letters, then dash/dot/colon parts that contain a digit) are removed first.
#   G4  the evidence numbers are those written in the brief's facts, candidates (value and description), signal and the
#       resource-spend line. Text from `untrusted` (tags, names) is never evidence (G8 is the one narrow exception): an injected "$99,999" grounds nothing.
#   G5  match: |n - k| <= max(1% of |k|, half a unit of the last decimal place n was written with). "6" matches "6.0";
#       "$1,468.8" matches 1468.80. A percentage n% also matches a ratio k = n/100, and a ratio matches a percentage.
#   G6  no exemption by size: small integers ("4 台", "6 倍") are checked like any other number. (The first version exempted
#       bare integers below 100 and accepted any n within 0.5 of a 3-digit k.)
#   G7  calendar words are not amounts: "7 月", "12 日" are removed with the dates (G2). A model translating "July" must not be rejected.
#   G8  quoting an attack: the prompt tells the model to mention instructions found in tags. When the verdict is not `waste`
#       (no finding is created, the text is a log line) a number that occurs in the untrusted metadata is tolerated, so that
#       "the Name tag asks for $4,000" does not discard a correct not_waste. For a `waste` verdict the same number is rejected:
#       the text becomes the finding's reasoning, and an attacker-chosen figure must not be displayed as a claim. Known residual
#       risk: number bait inside the metadata of a really wasteful fleet makes the model quote it and the finding is rejected
#       (fail closed, recorded in the trace with the number as reason). See eval/EXPERIMENTS.md.
NUM = re.compile(r"(?<![A-Za-z0-9_.])\$?\d[\d,]*(?:\.\d+)?%?")
DATE = re.compile(r"\d{4}-\d{2}(-\d{2})?|(?<![\d.])\d{1,2}-\d{2}(?![\d-])|\d{1,2}:\d{2}(:\d{2})?|\d{1,2}\s*月(?:\s*\d{1,2}\s*[日号])?|\d{1,2}\s*[日号]")
IDENT = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:[-.:][A-Za-z0-9_]+)+|[A-Za-z]+\d[A-Za-z0-9_]*")


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


def _clean(t: str) -> str:
    return IDENT.sub(" ", DATE.sub(" ", t))


def _num(s: str) -> float:
    return float(s.strip("$%").replace(",", ""))


def _decimals(raw: str) -> int:
    body = raw.strip("$%").replace(",", "")
    return len(body.split(".")[1]) if "." in body else 0


def _evidence_numbers(b: Brief) -> list:
    nums = []
    texts = [e.what for e in b.facts] + [f"{c.value:.2f} {c.desc}" for c in b.candidates] + [b.signal]
    if b.resource_spend_usd is not None:
        texts.append(f"{b.resource_spend_usd:.2f}")
    for t in texts:
        for m in NUM.finditer(_clean(t)):
            nums.append(_num(m.group()))
    return nums


def _matches(raw: str, k: float) -> bool:
    n, half = _num(raw), 0.5 * 10 ** -_decimals(raw)
    scaled = [(n, half), (n / 100, half / 100)] if raw.endswith("%") else [(n, half)] + ([(n * 100, half * 100)] if n <= 1 else [])
    return any(abs(v - k) <= max(0.01 * abs(k), h) for v, h in scaled)


def _untrusted_numbers(b: Brief) -> list:
    return [_num(m.group()) for v in b.untrusted.values() for t in map(str, v.values()) for m in NUM.finditer(_clean(t))]


def ungrounded_numbers(text: str, b: Brief, quoting_ok: bool = False) -> list:
    """Numbers in free text that appear nowhere in the evidence (rules G1-G8 above).
    quoting_ok: also accept numbers that occur in the untrusted metadata (G8, non-waste verdicts only)."""
    known = _evidence_numbers(b) + (_untrusted_numbers(b) if quoting_ok else [])
    return [m.group() for m in NUM.finditer(_clean(text)) if not any(_matches(m.group(), k) for k in known)]


def validate(raw: str, b: Brief, protected: set | None = None) -> Judgment:
    d = extract_json(raw)
    v = d.get("verdict")
    if v not in VERDICTS:
        raise Rejected(f"verdict {v!r} not in {VERDICTS}")
    texts = " ".join(str(d.get(k, "")) for k in ("title", "reasoning")) + " " + " ".join(map(str, d.get("hops") or []))
    bad = ungrounded_numbers(texts, b, quoting_ok=(v != "waste"))
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
