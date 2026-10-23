"""A Brief is everything the judge may see about one lead: facts, numeric candidates, and the
resources a finding may name. All numbers in it were computed by code (FA03)."""
from __future__ import annotations

from dataclasses import dataclass, field

from finops_agent.analyze import Evidence

ZERO = "none"


@dataclass
class Candidate:
    key: str
    value: float
    basis: str          # billed | billed_14d_extrapolated | list_price | inferred
    desc: str


@dataclass
class Brief:
    lead_id: str
    kind: str
    signal: str
    questions: list
    facts: list = field(default_factory=list)          # list[Evidence]; the judge cites them as E1, E2, ...
    candidates: list = field(default_factory=list)     # list[Candidate]
    resources: list = field(default_factory=list)      # ids a finding may name
    untrusted: dict = field(default_factory=dict)      # resource id -> raw metadata (tags); quoted data only
    resource_spend_usd: float | None = None
    default_step: str = ""
    scope: str = ""                                     # what this lead is responsible for, and what other leads cover

    def fact_ids(self):
        return {f"E{i + 1}": e for i, e in enumerate(self.facts)}

    def candidate(self, key):
        return next((c for c in self.candidates if c.key == key), None)
