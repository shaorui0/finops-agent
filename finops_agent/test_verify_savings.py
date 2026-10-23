import unittest
from datetime import date, timedelta
from fractions import Fraction as F

from finops_agent import verify_savings as v

KEY_G = "gp2_to_gp3|vol-x"


def period(label, start, end, items, findings=(), diff=None):
    """items: {(resource_id, usage_type): (daily_unblended, first_offset, last_offset_exclusive or None, daily_amortized or None)}"""
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    lines = {}
    for (rid, ut), spec in items.items():
        daily, a, b, am = (tuple(spec) + (0, None, None))[:4] if len(spec) < 4 else spec
        b = (e - s).days if b is None else b
        am = daily if am is None else am
        lines[(rid, ut)] = {s + timedelta(days=k): (F(daily), F(am)) for k in range(a, b)}
    return v.Period(label, s, e, list(findings), diff or {"new": [], "persisting": [], "resolved": [], "regressed": []}, lines)


def fnd(id_, type_, res, usd, basis="list_price", spend=None):
    return {"id": id_, "type": type_, "resources": res, "monthly_savings_usd": usd, "basis": basis, "resource_spend_usd": spend}


CTRL = {("vol-c", "EBS:VolumeUsage.gp2"): (F(1), 0, None)}      # untouched control volume, $1/day
CONV = fnd("F1", "gp2_to_gp3", ["vol-x"], 20, "list_price", 100)


class GP3(unittest.TestCase):
    """gp2 -> gp3 in period 2, reverted by an unrelated apply in period 3 (the month_after story)."""

    def setUp(self):
        gp2, gp3 = F(100, 30), F(80, 30)
        self.p = [
            period("A", "2026-09-01", "2026-10-01", {("vol-x", "EBS:VolumeUsage.gp2"): (gp2, 0, None), **CTRL}, [CONV]),
            period("B", "2026-10-01", "2026-11-01", {("vol-x", "EBS:VolumeUsage.gp3"): (gp3, 0, None), **CTRL}, [],
                   {"new": [], "persisting": [], "resolved": [{"key": KEY_G}], "regressed": []}),
            period("C", "2026-11-01", "2026-12-01", {("vol-x", "EBS:VolumeUsage.gp2"): (gp2, 0, None), **CTRL}, [CONV],
                   {"new": [], "persisting": [], "resolved": [], "regressed": [{"key": KEY_G, "finding": "F1", "resolved_in": "r2"}]}),
        ]
        self.res = v.analyze(self.p)

    def test_realized_then_lost(self):
        (x,) = self.res["verifications"]
        self.assertEqual(x["now"]["realized_std"], 20)
        self.assertEqual(x["verdict"], "ok")
        self.assertEqual(x["retained_std"], 0)
        self.assertEqual(x["lost_std"], 20)
        self.assertTrue(x["regressed_later"])
        self.assertEqual(x["final"], "兑现后丢失")

    def test_regression_is_priced_in_the_bill(self):
        d = self.res["decompositions"][1]
        self.assertEqual(d["parts"]["regression"], 20)
        self.assertEqual(d["parts"]["verified"], 0)


class Decomposition(unittest.TestCase):
    def test_sums_exactly_to_the_bill_delta(self):
        n, m = F(1, 3), F(7, 11)       # awkward rates: float arithmetic would not close
        a = period("A", "2026-09-01", "2026-10-01", {
            ("vol-o", "EBS:VolumeUsage.gp2"): (n, 0, None), ("vol-x", "EBS:VolumeUsage.gp2"): (m, 0, None),
            ("vol-c", "EBS:VolumeUsage.gp2"): (m, 0, None), (None, "NAT-Bytes"): (n, 0, None),
            ("vol-gone", "EBS:VolumeUsage.gp2"): (n, 0, None)},
            [fnd("F1", "unattached_volume", ["vol-o"], 10, "billed_14d_extrapolated"), CONV])
        b = period("B", "2026-10-01", "2026-11-01", {
            ("vol-x", "EBS:VolumeUsage.gp3"): (m * F(4, 5), 0, None), ("vol-c", "EBS:VolumeUsage.gp2"): (m * F(6, 5), 0, None),
            (None, "NAT-Bytes"): (n * 3, 0, None), ("vol-new", "EBS:VolumeUsage.gp3"): (n, 10, None),
            ("eip-surprise", "PublicIPv4:IdleAddress"): (n, 0, None)},
            [fnd("F9", "unattached_volume", ["vol-new"], 5, "billed_14d_extrapolated")],
            {"new": [{"key": "unattached_volume|vol-new", "finding": "F9"}], "persisting": [],
             "resolved": [{"key": "unattached_volume|vol-o"}, {"key": KEY_G}], "regressed": []})
        res = v.analyze([a, b])
        d = res["decompositions"][0]
        self.assertEqual(sum(p.cost_u for p in a.resources().values()), a.bill_u)
        self.assertEqual(d["sum"], d["delta"])           # Fraction equality, not assertAlmostEqual
        self.assertTrue(d["exact"])
        self.assertEqual(d["delta"], b.bill_u - a.bill_u)
        self.assertEqual(d["parts"]["new_waste"], b.resources()["vol-new"].cost_u)
        self.assertEqual(d["parts"]["other_removed"], -a.resources()["vol-gone"].cost_u)
        self.assertEqual(d["parts"]["other_new"], b.resources()["eip-surprise"].cost_u)


class Confounders(unittest.TestCase):
    def pair(self, growth):
        """Resource x is converted (cost x0.8 on its own). All control volumes' usage moves by `growth`."""
        a = period("A", "2026-09-01", "2026-10-01", {("snap-x", "EBS:SnapshotUsage"): (F(10), 0, None),
                                                      ("snap-c1", "EBS:SnapshotUsage"): (F(10), 0, None),
                                                      ("snap-c2", "EBS:SnapshotUsage"): (F(30), 0, None)},
                   [fnd("F1", "orphan_snapshots", ["snap-x"], 60, "billed")])
        b = period("B", "2026-10-01", "2026-11-01", {("snap-x", "EBS:SnapshotUsage"): (F(10) * F(1) * (1 + growth) * F(1, 2), 0, None),
                                                      ("snap-c1", "EBS:SnapshotUsage"): (F(10) * (1 + growth), 0, None),
                                                      ("snap-c2", "EBS:SnapshotUsage"): (F(30) * (1 + growth), 0, None)},
                   [], {"new": [], "persisting": [], "resolved": [{"key": "orphan_snapshots|snap-x"}], "regressed": []})
        return v.analyze([a, b])["verifications"][0]["now"]

    def test_usage_growth_is_separated_from_the_saving(self):
        # x halves its cost in a stratum whose usage also grows 50%. Two invoices show 10 -> 7.5 = 2.5 saved; against the
        # do-nothing counterfactual (15) the change alone saved 7.5. The adjusted number is the effect of the change only.
        g = F(1, 2)
        now = self.pair(g)
        self.assertEqual(now["drift"]["ebs_snapshot"]["g"], 1 + g)
        self.assertEqual(now["realized_std"], now["cf_std"] - now["act_std"])
        self.assertEqual(now["realized_std"] / now["baseline_std"], F(1, 2) * (1 + g))   # half of what x would have cost
        self.assertNotEqual(now["naive_std"], now["realized_std"])

    def test_usage_decline_does_not_inflate_the_saving(self):
        now = self.pair(F(-1, 2))                  # everything falls 50% on its own; x falls to a quarter
        self.assertEqual(now["naive_std"], now["baseline_std"] * F(3, 4))       # naive: 75% "saved"
        self.assertEqual(now["realized_std"], now["baseline_std"] * F(1, 4))    # adjusted: only the extra 25% is ours
        self.assertLess(now["realized_std"], now["naive_std"])

    def test_no_drift_leaves_naive_and_adjusted_equal(self):
        now = self.pair(F(0))
        self.assertEqual(now["naive_std"], now["realized_std"])


class Proration(unittest.TestCase):
    def test_created_mid_period_then_deleted(self):
        # created on day 8 of a 31-day month at $1/day; deleted before the next 30-day month starts
        a = period("A", "2026-10-01", "2026-11-01", {("vol-n", "EBS:VolumeUsage.gp3"): (F(1), 7, None)},
                   [fnd("F1", "unattached_volume", ["vol-n"], 31, "billed_14d_extrapolated")])
        b = period("B", "2026-11-01", "2026-12-01", {("vol-z", "EBS:VolumeUsage.gp3"): (F(1), 0, None)}, [],
                   {"new": [], "persisting": [], "resolved": [{"key": "unattached_volume|vol-n"}], "regressed": []})
        (x,) = v.analyze([a, b])["verifications"]
        n = x["now"]
        self.assertEqual(n["baseline_std"], 30)            # run-rate, not the 24 days actually billed
        self.assertEqual(n["naive_cal"], 24)               # what the two invoices show
        self.assertEqual(x["predicted"], 30)               # 31-day extrapolation scaled to a standard month
        self.assertEqual(x["verdict"], "ok")
        self.assertIn("proration", [d[0] for d in x["devs"]])

    def test_deleted_mid_period_counts_the_steady_state(self):
        a = period("A", "2026-09-01", "2026-10-01", {("vol-d", "EBS:VolumeUsage.gp2"): (F(2), 0, None)},
                   [fnd("F1", "unattached_volume", ["vol-d"], 60, "billed")])
        b = period("B", "2026-10-01", "2026-11-01", {("vol-d", "EBS:VolumeUsage.gp2"): (F(2), 0, 10)}, [],     # deleted on day 11
                   {"new": [], "persisting": [], "resolved": [{"key": "unattached_volume|vol-d"}], "regressed": []})
        (x,) = v.analyze([a, b])["verifications"]
        self.assertEqual(x["now"]["realized_std"], 60)                  # steady state: fully gone
        self.assertEqual(x["now"]["realized_cal"], 2 * 31 - 20)         # first month cash: 21 days saved
        self.assertIn("proration", [d[0] for d in x["devs"]])


class Commitment(unittest.TestCase):
    def test_amortized_saving_absorbed_by_unused_commitment(self):
        ut = "BoxUsage:m5.large"
        a = period("A", "2026-09-01", "2026-10-01", {("i-1", ut): (F(0), 0, None, F(3)), ("sp-1", "SavingsPlanRecurringFee"): (F(10), 0, None, F(0))},
                   [fnd("F1", "stopped_instance", ["i-1"], 90, "list_price")])
        b = period("B", "2026-10-01", "2026-11-01", {("sp-1", "SavingsPlanRecurringFee"): (F(10), 0, None, F(3))}, [],
                   {"new": [], "persisting": [], "resolved": [{"key": "stopped_instance|i-1"}], "regressed": []})
        (x,) = v.analyze([a, b])["verifications"]
        self.assertEqual(x["now"]["realized_std"], 0)                   # the bill did not move
        self.assertEqual(x["now"]["realized_amort_std"], 90)           # the amortized view says $90
        self.assertEqual(x["verdict"], "none")
        self.assertIn("commitment", [d[0] for d in x["devs"]])


class EndToEnd(unittest.TestCase):
    """Real servers and real agent runs on ports 34590-34591 (the repo's test range is 34566-34599)."""

    @classmethod
    def setUpClass(cls):
        cls.periods = v.collect(34590)
        cls.res = v.analyze(cls.periods)

    def test_resolved_sets_match_scenario_expectations(self):
        for p in self.periods[1:]:
            self.assertEqual(sorted(e["key"] for e in p.diff["resolved"]), sorted(p.expect["resolved"]))

    def test_gp3_realized_in_october_lost_in_november(self):
        x = next(x for x in self.res["verifications"] if x["type"] == "gp2_to_gp3")
        self.assertEqual(x["verdict"], "ok")
        self.assertAlmostEqual(float(x["now"]["realized_std"]), 20, places=3)
        self.assertAlmostEqual(float(x["retained_std"]), 0, places=3)
        self.assertEqual(x["final"], "兑现后丢失")

    def test_bills_decompose_exactly(self):
        for d in self.res["decompositions"]:
            self.assertTrue(d["exact"])
            self.assertEqual(d["sum"], d["delta"])

    def test_document_is_deterministic(self):
        first, _ = v.build(self.res)
        again = v.analyze(v.collect(34592))
        second, _ = v.build(again)
        self.assertEqual(v.to_md(first), v.to_md(second))

    def test_deletions_realize_the_predicted_amount(self):
        for x in self.res["verifications"]:
            if x["type"] in ("unattached_volume", "idle_public_ip"):
                self.assertEqual(x["verdict"], "ok", x["key"])


if __name__ == "__main__":
    unittest.main()
