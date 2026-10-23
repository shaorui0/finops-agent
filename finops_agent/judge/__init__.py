"""Judgment layer: an LLM answers the deterministic leads, each in its own isolated call.

lead -> gather (code computes the evidence and candidate numbers) -> prompt (that lead only)
     -> LLM (record/replay client) -> validate (strict JSON, grounded numbers, allowed resources)
     -> Finding (savings come from the chosen candidate, never from the model's text)
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from finops_agent.analyze import Evidence, Finding, Lead
from finops_agent.judge import gather, prompt, validate
from finops_agent.judge.brief import ZERO, Brief
from finops_agent.llm import CassetteMissing, LLMClient

MAX_WORKERS = 4


def _call(client: LLMClient, text: str):
    t0 = time.time()
    r = client.complete(text)
    return r, round((time.time() - t0) * 1000, 1)


def protected_resources(cx: gather.Ctx, ids) -> set:
    out = set()
    for i in ids:
        inst = cx.inst.get(i)
        if inst and any(k.lower() in validate.PROTECTIVE_TAG_KEYS for k in gather._tags(inst)):
            out.add(i)
    return out


def judge_leads(leads: list[Lead], cx: gather.Ctx, client: LLMClient, trace, next_id: int):
    """Returns (findings, judgments). One trace entry per LLM call."""
    briefs = [gather.build(l, cx) for l in leads]
    prompts = [prompt.render(b) for b in briefs]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futs = [pool.submit(_call, client, p) for p in prompts]
        outcomes = []
        for f in futs:
            try:
                outcomes.append(f.result())
            except CassetteMissing:
                raise                              # a missing cassette is never silent
            except Exception as e:                 # a failed live call is recorded, the lead stays unjudged
                outcomes.append(e)
    findings, judgments = [], []
    for lead, b, out in zip(leads, briefs, outcomes):
        j = {"lead": lead.id, "kind": lead.kind, "verdict": None, "accepted": False, "reject_reason": None, "finding": None,
             "title": None, "reasoning": None, "key": None}
        entry = {"source": "llm", "op": "judge", "params": {"lead": lead.id, "kind": lead.kind, "model": client.model},
                 "ms": None, "ok": True, "error": None, "mode": client.mode, "tokens_in": 0, "tokens_out": 0,
                 "latency_ms": 0.0, "cost_usd": 0.0}
        if isinstance(out, Exception):
            entry.update(ok=False, error=str(out))
            j["reject_reason"] = f"llm call failed: {out}"
        else:
            res, wall = out
            entry.update(ms=wall, tokens_in=res.tokens_in, tokens_out=res.tokens_out, latency_ms=res.latency_ms,
                         cost_usd=res.cost_usd, key=res.key)
            j["key"] = res.key
            try:
                jd = validate.validate(res.text, b, protected_resources(cx, b.resources))
                j.update(verdict=jd.verdict, title=jd.title, reasoning=jd.reasoning, accepted=True)
                if jd.verdict == "waste":
                    f = to_finding(f"F{next_id + len(findings):02d}", lead, b, jd, res.key)
                    findings.append(f)
                    j["finding"] = f.id
            except validate.Rejected as e:
                j["reject_reason"] = str(e)
        entry["verdict"], entry["accepted"], entry["reject_reason"] = j["verdict"], j["accepted"], j["reject_reason"]
        trace.calls.append(entry)
        judgments.append(j)
    return findings, judgments


def to_finding(fid: str, lead: Lead, b: Brief, jd: validate.Judgment, key: str) -> Finding:
    cand = b.candidate(jd.savings_choice) if jd.savings_choice != ZERO else None
    savings = cand.value if cand else 0.0
    ev = [b.fact_ids()[e] for e in jd.evidence]
    ev.append(Evidence("llm", jd.reasoning, f"judge {lead.id} cassette {key[:12]}"))
    if cand:
        ev.append(Evidence("computed", f"节省 {savings:,.2f} 取自候选 {cand.key}：{cand.desc}", "judge candidates"))
    return Finding(fid, jd.type, jd.method_step, jd.title, jd.resources, jd.hops, ev, savings,
                   cand.basis if cand else "none", b.resource_spend_usd, f"judge:{lead.kind}")
