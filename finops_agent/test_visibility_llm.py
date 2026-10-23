import re
import tempfile
import unittest
from pathlib import Path

import yaml

from eval.score_visibility import REVIEWED, PROBES, load, name_overlap, score, scope_overlap, server_metric_names
from finops_agent import visibility
from finops_agent.llm import LLMClient
from finops_agent.visibility_llm import ROOT, build_prompt, derive, extract_json, validate

GOALS = ROOT / "config" / "cost_goals.yaml"
SNAP = {"instances": [{"InstanceId": "i-1", "State": {"Name": "running"}}], "nat_gateways": [{"NatGatewayId": "nat-1"}]}


def literals(regex: str) -> set[str]:
    """Metric-name-looking literal fragments inside a regex (identifier runs with an underscore, >= 10 chars)."""
    return {m for m in re.findall(r"[A-Za-z0-9_]{10,}", regex) if "_" in m}


class PromptHygieneTest(unittest.TestCase):
    """Goal-first (FA12): the model must not see any metric name from the server or from the reviewed file."""

    def setUp(self):
        self.prompt = build_prompt(GOALS.read_text())

    def test_no_metric_name_from_the_server(self):
        for name in server_metric_names():
            self.assertNotIn(name, self.prompt)

    def test_no_literal_from_the_reviewed_requirements(self):
        reviewed = load(REVIEWED)
        for s in reviewed:
            self.assertNotIn(s["id"], self.prompt)
            for n in s["need"]:
                for lit in literals(n["name"]):
                    self.assertNotIn(lit, self.prompt, f"{lit!r} from the reviewed file leaked into the prompt")

    def test_goals_file_has_no_metric_names_or_sli_ids(self):
        text = GOALS.read_text()
        for name in server_metric_names():
            self.assertNotIn(name, text)
        for s in load(REVIEWED):
            self.assertNotIn(s["id"], text)

    def test_prompt_contains_the_goals(self):
        for g in yaml.safe_load(GOALS.read_text())["goals"]:
            self.assertIn(g["目标"], self.prompt)


class DeriveTest(unittest.TestCase):
    def test_replay_produces_valid_ring1_usable_by_rings_2_to_4(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "r1.yaml"
            d = derive(GOALS, out, LLMClient("replay"))   # fails with CassetteMissing if the prompt changed without re-recording
            self.assertEqual(d["_call"]["mode"], "replay")
            slis = visibility.ring1(out)
            self.assertEqual(validate({"slis": slis}), [])
            plan = visibility.ring2(slis, SNAP)
            self.assertEqual(len(plan), sum(len(s["need"]) for s in slis))
            self.assertTrue(yaml.safe_load(out.read_text())["not_metric_observable"])

    def test_validate_rejects_bad_scope_and_regex(self):
        bad = {"slis": [{"id": "x", "decision": "d", "need": [{"signal": "s", "name": "a(", "scope": "everything"}]}]}
        errs = validate(bad)
        self.assertTrue(any("bad scope" in e for e in errs) and any("bad regex" in e for e in errs))

    def test_extract_json_handles_fences_and_prose(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(extract_json('here: {"a": 2} done'), {"a": 2})


class ScoreTest(unittest.TestCase):
    NAMES = server_metric_names()

    def test_reviewed_against_itself_is_perfect(self):
        r = load(REVIEWED)
        res = score(r, r, self.NAMES)
        self.assertEqual((res["recall"], res["precision"]), (1.0, 1.0))

    def test_scope_must_overlap(self):
        r = [{"id": "a", "decision": "d", "need": [{"signal": "s", "name": "aws_ec2_cpuutilization_average", "scope": "running_instances"}]}]
        d = [{"id": "b", "decision": "d", "need": [{"signal": "s", "name": "aws_ec2_cpuutilization_.*", "scope": "services:web"}]}]
        res = score(r, d, self.NAMES)
        self.assertEqual(res["recall"], 0.0)
        self.assertEqual(res["recall_name_only"], 1.0)
        self.assertTrue(scope_overlap("services:web,api", "services:api"))
        self.assertFalse(scope_overlap("services:web", "running_instances"))

    def test_wildcard_regex_does_not_count(self):
        self.assertFalse(name_overlap("aws_ec2_cpuutilization_average", ".*", self.NAMES | set(PROBES)))

    def test_probe_names_let_planted_gaps_be_compared(self):
        self.assertTrue(name_overlap(".*mem.*", "(CWAgent_)?mem_used_percent", self.NAMES | set(PROBES)))

    def test_extra_derived_needs_are_split_by_whether_they_exist(self):
        r = load(REVIEWED)[:1]
        d = [{"id": "x", "decision": "d", "need": [{"signal": "s", "name": "no_such_metric_total", "scope": "nat_gateways"},
                                                  {"signal": "s", "name": "up", "scope": "nat_gateways"}]}]
        kinds = {e["name"]: e["kind"] for e in score(r, d, self.NAMES)["extra"]}
        self.assertIn("no metric", kinds["no_such_metric_total"])
        self.assertIn("real metrics", kinds["up"])


if __name__ == "__main__":
    unittest.main()
