import unittest
from datetime import date

from finops_agent.slo import diff_state, evaluate, to_prometheus

F = lambda id, type, res: {"id": id, "type": type, "resources": res, "monthly_savings_usd": 1.0, "basis": "billed"}
VOL, EIP, SNAP = F("F1", "unattached_volume", ["vol-a"]), F("F2", "idle_public_ip", ["eip-a"]), F("F3", "orphan_snapshots", ["vol-x"])


class DiffStateTest(unittest.TestCase):
    def test_lifecycle_new_persist_resolve_regress(self):
        d1, s1 = diff_state([VOL, EIP], None, "r1", date(2026, 10, 1))
        self.assertEqual((len(d1["new"]), len(d1["persisting"])), (2, 0))
        d2, s2 = diff_state([VOL], s1, "r2", date(2026, 10, 8))          # EIP released
        self.assertEqual([x["key"] for x in d2["resolved"]], ["idle_public_ip|eip-a"])
        self.assertEqual(len(d2["persisting"]), 1)
        d3, s3 = diff_state([VOL, EIP, SNAP], s2, "r3", date(2026, 10, 15))  # EIP is back, snapshot new
        self.assertEqual([x["key"] for x in d3["regressed"]], ["idle_public_ip|eip-a"])
        self.assertEqual(d3["regressed"][0]["resolved_in"], "r2")
        self.assertEqual([x["key"] for x in d3["new"]], ["orphan_snapshots|vol-x"])
        self.assertEqual(s3["first_seen"]["unattached_volume|vol-a"], "2026-10-01")

    def test_same_resource_different_type_is_a_different_finding(self):
        _, s1 = diff_state([VOL], None, "r1", date(2026, 10, 1))
        d2, _ = diff_state([F("F9", "gp2_to_gp3", ["vol-a"])], s1, "r2", date(2026, 10, 2))
        self.assertEqual(len(d2["new"]), 1)
        self.assertEqual(len(d2["resolved"]), 1)


def mksnap(volumes=(), cost=None):
    """Minimal snapshot: volumes are (id, VolumeType, Size); cost = {resource id: 14-day USD}."""
    groups = [{"Keys": [r], "Metrics": {"UnblendedCost": {"Amount": str(c)}}} for r, c in (cost or {}).items()]
    return {"resource_period": {"Start": "2026-10-18", "End": "2026-11-01"}, "cost_by_resource_14d": [{"Groups": groups}],
            "volumes": [{"VolumeId": i, "State": "available", "VolumeType": t, "Size": z, "Attachments": []} for i, t, z in volumes]}


class NotRedetectedTest(unittest.TestCase):
    """A finding that vanishes is `resolved` only with evidence the resource changed; otherwise it was just not re-detected."""
    GP2 = F("F1", "gp2_to_gp3", ["vol-a"])

    def run1(self, snap):
        return diff_state([self.GP2], None, "r1", date(2026, 10, 1), snap)

    def test_resource_still_there_and_unchanged_is_not_redetected_not_resolved(self):
        snap = mksnap([("vol-a", "gp2", 100)], {"vol-a": 14.0})
        _, s1 = self.run1(snap)
        d2, s2 = diff_state([], s1, "r2", date(2026, 11, 1), snap)
        self.assertEqual(d2["resolved"], [])
        self.assertEqual([x["key"] for x in d2["not_redetected"]], ["gp2_to_gp3|vol-a"])
        self.assertNotIn("gp2_to_gp3|vol-a", s2["resolved"])      # so a later reappearance is not called a regression

    def test_resource_absent_is_resolved(self):
        _, s1 = self.run1(mksnap([("vol-a", "gp2", 100)], {"vol-a": 14.0}))
        d2, _ = diff_state([], s1, "r2", date(2026, 11, 1), mksnap())
        self.assertEqual([x["key"] for x in d2["resolved"]], ["gp2_to_gp3|vol-a"])
        self.assertEqual(d2["not_redetected"], [])

    def test_type_changed_in_place_is_resolved(self):
        _, s1 = self.run1(mksnap([("vol-a", "gp2", 100)], {"vol-a": 14.0}))
        d2, _ = diff_state([], s1, "r2", date(2026, 11, 1), mksnap([("vol-a", "gp3", 100)], {"vol-a": 11.2}))
        self.assertEqual(len(d2["resolved"]), 1)

    def test_cost_line_dropped_is_resolved(self):
        _, s1 = self.run1(mksnap([("vol-a", "gp2", 100)], {"vol-a": 14.0}))
        d2, _ = diff_state([], s1, "r2", date(2026, 11, 1), mksnap([("vol-a", "gp2", 100)], {"vol-a": 1.0}))
        self.assertEqual(len(d2["resolved"]), 1)

    def test_not_redetected_persists_then_resolves_then_regresses(self):
        snap = mksnap([("vol-a", "gp2", 100)], {"vol-a": 14.0})
        _, s1 = self.run1(snap)
        d2, s2 = diff_state([], s1, "r2", date(2026, 11, 1), snap)
        d3, s3 = diff_state([], s2, "r3", date(2026, 12, 1), snap)
        self.assertEqual(d3["not_redetected"][0]["since"], "r2")           # still the same missed detection
        d4, s4 = diff_state([], s3, "r4", date(2027, 1, 1), mksnap())        # now the volume is gone
        self.assertEqual(len(d4["resolved"]), 1)
        d5, _ = diff_state([self.GP2], s4, "r5", date(2027, 2, 1), mksnap([("vol-a", "gp2", 100)], {"vol-a": 14.0}))
        self.assertEqual(len(d5["regressed"]), 1)

    def test_redetected_after_a_miss_is_persisting(self):
        snap = mksnap([("vol-a", "gp2", 100)], {"vol-a": 14.0})
        _, s1 = self.run1(snap)
        _, s2 = diff_state([], s1, "r2", date(2026, 11, 1), snap)
        d3, s3 = diff_state([self.GP2], s2, "r3", date(2026, 12, 1), snap)
        self.assertEqual((len(d3["persisting"]), len(d3["regressed"]), s3["not_redetected"]), (1, 0, {}))

    def test_without_a_snapshot_the_old_behavior_holds(self):
        _, s1 = diff_state([self.GP2], None, "r1", date(2026, 10, 1))
        d2, _ = diff_state([], s1, "r2", date(2026, 11, 1))
        self.assertEqual((len(d2["resolved"]), d2["not_redetected"]), (1, []))

    def test_prometheus_state_label_includes_not_redetected(self):
        d = {"new": [], "persisting": [], "resolved": [], "regressed": [], "not_redetected": [1, 2]}
        self.assertIn('finops_findings{state="not_redetected"} 2', to_prometheus([], d, "r1", 1.0))


class EvaluateTest(unittest.TestCase):
    CFG = {"slos": [
        {"id": "waste_ratio", "what": "", "op": "<=", "target": 0.05, "budget": True, "cadence": "daily"},
        {"id": "commitment_utilization", "what": "", "op": ">=", "target": 0.9, "cadence": "monthly"},
        {"id": "remediation_age_days", "what": "", "op": "<=", "target": 30, "cadence": "weekly"},
    ]}

    def test_status_and_budget(self):
        rows = {r["id"]: r for r in evaluate({"values": {"waste_ratio": 0.10, "commitment_utilization": 0.95},
                                              "evidence": {}, "spend": 1000.0, "waste": 100.0}, self.CFG)}
        self.assertEqual(rows["waste_ratio"]["status"], "violated")
        self.assertAlmostEqual(rows["waste_ratio"]["budget_used"], 2.0)
        self.assertEqual(rows["commitment_utilization"]["status"], "ok")
        self.assertEqual(rows["remediation_age_days"]["status"], "no_data")

    def test_prometheus_export(self):
        rows = evaluate({"values": {"waste_ratio": 0.10}, "evidence": {}, "spend": 1000.0, "waste": 100.0}, self.CFG)
        text = to_prometheus(rows, {"new": [1], "persisting": [], "resolved": [], "regressed": []}, "r1", 1.0)
        self.assertIn('finops_sli{sli="waste_ratio",run="r1"} 0.1', text)
        self.assertIn('finops_findings{state="new"} 1', text)
        self.assertIn("finops_waste_budget_used 2", text)
        self.assertNotIn('sli="remediation_age_days",run', text)


if __name__ == "__main__":
    unittest.main()
