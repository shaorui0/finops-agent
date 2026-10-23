"""Held-out evaluation: expected ground truth per scenario, and the replayed metrics (pinned, so a change shows up)."""
import json
import unittest

from eval import heldout
from eval.score import gates

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
    """Replay of the cassettes recorded in c0015. Pinned numbers: these are results, not targets."""

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
        self.assertEqual((n["recall"], n["savings_recall"], n["precision"]), (0.9, 0.5658, 1.0))
        self.assertEqual((m["recall"], m["savings_recall"], m["precision"]), (0.9091, 0.5664, 1.0))
        self.assertEqual([x["id"] for x in n["missed"]], ["GT02"])
        self.assertEqual([x["id"] for x in m["missed"]], ["GT02"])

    def test_held_out_is_not_better_than_in_sample(self):
        base = self.res["base (in-sample)"]
        for w in ("next_month", "month_after"):
            self.assertLess(self.res[w]["recall"], base["recall"])
            self.assertLess(self.res[w]["savings_recall"], base["savings_recall"])

    def test_no_trap_or_invariant_violations_and_every_judgment_accepted(self):
        for name, r in self.res.items():
            self.assertEqual(r["trap_violations"], [], name)
            self.assertEqual(r["invariants"], [], name)
            self.assertTrue(all(j["accepted"] for j in r["judged"]), name)

    def test_the_gate_failures_are_only_the_recall_regression(self):
        for w in ("next_month", "month_after"):
            self.assertEqual(gates(self.res[w], BASE_METRICS) and [f.split()[0] for f in gates(self.res[w], BASE_METRICS)], ["recall", "savings_recall"])


if __name__ == "__main__":
    unittest.main()
