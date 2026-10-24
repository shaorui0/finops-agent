"""Held-out evaluation: expected ground truth per scenario, and the replayed metrics (pinned, so a change shows up)."""
import json
import unittest
from collections import Counter

import yaml

from eval import heldout
from eval.score import gates
from testenv import world as world_mod

BASE_METRICS = json.loads((heldout.ROOT / "eval" / "baseline.json").read_text())


class ExpectedGroundTruthTest(unittest.TestCase):
    def ids(self, name):
        gt = heldout.expected_ground_truth(heldout.SCEN / name)
        return {g["id"]: g for g in gt["findings"]}

    def test_next_month_drops_three_resolved_and_adds_the_new_volume(self):
        g = self.ids("next_month.yaml")
        self.assertEqual(len(g), 10)
        self.assertNotIn("GT10", g)
        self.assertNotIn("GT11", g)
        self.assertEqual(g["GT09"]["resources"], ["vol-0new000000000e001"])
        self.assertAlmostEqual(g["GT09"]["monthly_savings_usd"]["min"], 15.2)    # 200 GB gp3 at $0.08 -5%

    def test_month_after_restores_the_regressed_volume_and_adds_the_leaked_ip(self):
        g = self.ids("month_after.yaml")
        self.assertEqual(len(g), 11)
        self.assertEqual(g["GT11"]["resources"], ["vol-0db0000000000a001"])
        self.assertEqual(g["GT10"]["resources"][0].startswith("eipalloc-0aa0000000000003"), True)
        self.assertNotIn("GT09", g)

    def test_traps_are_unchanged(self):
        base = heldout.base_ground_truth()["traps"]
        self.assertEqual(heldout.expected_ground_truth(heldout.SCEN / "next_month.yaml")["traps"], base)


class HeldoutReplayTest(unittest.TestCase):
    """Replay of the cassettes recorded in c0015 and c0023. Pinned numbers: these are results, not targets.

    c0023 changed the agent AFTER seeing the held-out miss of GT02 (see eval/EXPERIMENTS.md), so the held-out numbers
    below are contaminated for that failure: they show the fix works on those worlds, not how it generalizes."""

    @classmethod
    def setUpClass(cls):
        cls.res = heldout.run_all()

    def test_in_sample_equals_the_baseline(self):
        r = self.res["base (in-sample)"]
        for k in ("recall", "savings_recall", "precision", "savings_accuracy", "step_agreement"):
            self.assertEqual(r[k], BASE_METRICS[k], k)

    def test_held_out_metrics_are_reported_separately_and_pinned(self):
        n, m = self.res["next_month"], self.res["month_after"]
        self.assertEqual((n["kind"], m["kind"]), ("held-out", "held-out"))
        self.assertEqual((n["recall"], n["savings_recall"], n["precision"], n["savings_accuracy"]), (1.0, 1.0, 1.0, 0.8))   # c0015: 0.9 / 0.5658 / 1.0 / 0.8889
        self.assertEqual((m["recall"], m["savings_recall"], m["precision"], m["savings_accuracy"]), (1.0, 1.0, 1.0, 1.0))   # c0015: 0.9091 / 0.5664 / 1.0 / 1.0
        self.assertEqual([x["id"] for x in n["missed"]] + [x["id"] for x in m["missed"]], [])
        self.assertEqual([s["gt"] for s in n["savings_out_of_range"]], ["GT01", "GT02"])    # GT02 now found, 1.7% above its range

    def test_held_out_now_matches_in_sample_recall_because_the_fix_was_made_on_it(self):
        """Not evidence of generalization: c0023 targeted exactly the GT02 miss seen here. A fresh world is needed."""
        base = self.res["base (in-sample)"]
        for w in ("next_month", "month_after"):
            self.assertEqual(self.res[w]["recall"], base["recall"])
            self.assertEqual(self.res[w]["savings_recall"], base["savings_recall"])

    def test_no_trap_or_invariant_violations_and_every_judgment_accepted(self):
        for name, r in self.res.items():
            if name != "fresh_world":      # the fresh world has one trap violation, pinned in FreshWorldTest
                self.assertEqual(r["trap_violations"], [], name)
            self.assertEqual(r["invariants"], [], name)
            self.assertTrue(all(j["accepted"] for j in r["judged"]), name)

    def test_gates_pass_on_held_out_worlds(self):
        for w in ("next_month", "month_after"):
            self.assertEqual(gates(self.res[w], BASE_METRICS), [], w)


class FreshWorldGroundTruthTest(unittest.TestCase):
    """The preregistered world is internally consistent. These checks read the world, not the agent."""

    @classmethod
    def setUpClass(cls):
        cls.gt = yaml.safe_load(heldout.FRESH.read_text())["ground_truth"]
        world_mod.use(heldout.FRESH)
        cls.w = world_mod.load()
        cost = Counter()
        for l in cls.w.lines:
            if (l.day.year, l.day.month) == (2026, 6):
                cost[l.resource_id] += l.amortized
                cost[l.usage_type] += l.amortized
        cls.cost = cost
        cls.rng = {g["id"]: g["monthly_savings_usd"] for g in cls.gt["findings"]}

    @classmethod
    def tearDownClass(cls):
        world_mod.use(None)

    def test_preregistered_shape(self):
        f = self.gt["findings"]
        self.assertEqual((len(f), len(self.gt["traps"]), len(self.gt["visibility_gaps"])), (12, 5, 3))
        self.assertGreaterEqual(sum(len(g["hops"]) >= 3 for g in f), 4)
        self.assertEqual({g["method_step"][:2] for g in f}, {"M1", "M3", "M4", "M5", "M6"})
        self.assertTrue(any(t["must_not"] == "skip" for t in self.gt["traps"]))      # the injection
        for g in f + self.gt["traps"]:
            for part in ("status", "spec", "diff", "runbook", "prevention"):
                self.assertTrue(g.get(part), f"{g['id']} lacks {part}")

    def test_savings_ranges_contain_the_cost_model(self):
        c, r = self.cost, self.rng
        model = {
            "GT01": sum(c[f"i-0f1e2d3c4b5a6040{k}"] for k in range(1, 5)),
            "GT02": c["NatGateway-Bytes"],
            "GT03": c["DataTransfer-Regional-Bytes"],
            "GT05": c["vol-0f0recon00000b001"] + c["vol-0f0recon00000b002"],
            "GT06": c["vol-0f0dwh0000000c001"] + c["vol-0f0scratch00000c002"],
            "GT08": 175.0,        # 15 x 180 GB + 10 x 80 GB snapshots at 0.05
            "GT09": c["vol-0f0ledger00000a001"] - 1600 * 0.08,
            "GT10": c["i-0f1e2d3c4b5a60501"] * 22 / 24,
            "GT12": c["eipalloc-0bb0000000000001"] + c["eipalloc-0bb0000000000002"],
        }
        for gid, v in model.items():
            self.assertLessEqual(r[gid]["min"] - 0.01, v + 0.01, gid)
            self.assertGreaterEqual(r[gid]["max"] + 0.01, v - 0.01, gid)
        self.assertEqual((r["GT04"], r["GT07"]), ({"min": 0, "max": 0}, {"min": 0, "max": 0}))
        self.assertAlmostEqual(c["SavingsPlanRecurringFee"], 643.74, 2)


class FreshWorldResultTest(unittest.TestCase):
    """Pinned c0024 result: the single preregistered measurement (replayed from the cassettes recorded in commit B).

    These are results, not targets. No agent code changed in response (prereg.md section 5)."""

    @classmethod
    def setUpClass(cls):
        cls.r = heldout.run_all(only=["fresh_world"])["fresh_world"]

    def test_kind_and_headline_numbers(self):
        r = self.r
        self.assertEqual(r["kind"], "preregistered")
        self.assertEqual((r["recall"], r["savings_recall"], r["precision"], r["savings_accuracy"], r["step_agreement"]),
                         (0.75, 0.568, 1.0, 0.5385, 1.0))
        self.assertEqual(r["depth"], {"shallow_recall": 1.0, "deep_recall": 0.6667})
        self.assertEqual((r["findings_n"], r["gt_n"]), (13, 12))
        self.assertEqual(r["invariants"], [])

    def test_missed_and_trap_violation(self):
        self.assertEqual([m["id"] for m in self.r["missed"]], ["GT02", "GT03", "GT07"])
        self.assertEqual([(v["trap"], v["resource"], v["finding"]) for v in self.r["trap_violations"]],
                         [("TR05", "vol-0f0audit00000c003", "F03")])

    def test_llm_use_is_within_the_preregistered_budget(self):
        self.assertEqual(self.r["llm"]["calls"], 8)
        self.assertLessEqual(self.r["llm"]["calls"], 12)
        self.assertEqual(self.r["llm"]["cost_usd"], 0.1507)
        self.assertTrue(all(j["accepted"] for j in self.r["judged"]))

    def test_the_injected_resource_is_still_analysed_and_the_decoy_fleet_is_not_flagged(self):
        flagged = {x for f in self.r["findings"] for x in f[2]}
        self.assertIn("i-0f1e2d3c4b5a60801", flagged)          # TR04 (skip): analysed despite the Name tag
        for trap_resource in ("storefront-asg", "i-0f1e2d3c4b5a60701", "ami-web-v12", "ami-ingest-v7"):
            self.assertNotIn(trap_resource, flagged)            # TR01-TR03 held

    def test_is_lower_than_in_sample_and_the_contaminated_held_out(self):
        self.assertLess(self.r["recall"], BASE_METRICS["recall"])
        self.assertLess(self.r["savings_recall"], BASE_METRICS["savings_recall"])


if __name__ == "__main__":
    unittest.main()
