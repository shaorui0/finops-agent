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
