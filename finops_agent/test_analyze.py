"""Cost-shape leads: the in-window jump, and the anomaly that was already there when the window opened."""
import unittest
from datetime import date, timedelta

from finops_agent.analyze import Analyzer

UT = "NatGateway-Bytes"


def days(start, values, ut=UT):
    return [{"TimePeriod": {"Start": (start + timedelta(days=i)).isoformat()},
             "Groups": [{"Keys": [ut], "Metrics": {"UnblendedCost": {"Amount": str(v)}}}]} for i, v in enumerate(values)]


def analyzer(history, window, ut=UT):
    snap = {"resource_period": {"Start": "2026-10-18", "End": "2026-11-01"}, "cost_by_resource_14d": [],
            "cost_daily_by_usage_type": days(date(2026, 10, 1), window, ut),
            "cost_by_usage_type": [{"Groups": []}], "instances": []}
    if history is not None:
        snap["cost_history_daily_by_usage_type"] = days(date(2026, 7, 1), history, ut)
    a = Analyzer(snap, 31)
    a.leads_from_cost_shape()
    return a


class PersistentAnomalyTest(unittest.TestCase):
    def test_elevated_from_before_the_window_gets_a_lead_with_the_true_onset(self):
        hist = [10.0] * 65 + [60.0] * 27                      # incident began on history day 66 = 2026-09-04
        a = analyzer(hist, [60.0] * 31)
        self.assertEqual(len(a.leads), 1)
        l = a.leads[0]
        self.assertEqual((l.kind, l.params, l.since), ("cost_growth", {"usage_type": UT}, "2026-09-04"))

    def test_flat_cost_gets_no_lead(self):
        self.assertEqual(analyzer([10.0] * 92, [11.0] * 31).leads, [])

    def test_an_in_window_jump_keeps_its_single_lead(self):
        a = analyzer([10.0] * 92, [10.0] * 10 + [60.0] * 21)
        self.assertEqual(len(a.leads), 1)
        self.assertEqual(a.leads[0].since, "2026-10-11")
        self.assertIn("涨到", a.leads[0].signal)

    def test_no_history_means_no_baseline_and_no_lead(self):
        self.assertEqual(analyzer(None, [60.0] * 31).leads, [])
        self.assertEqual(analyzer([], [60.0] * 31).leads, [])

    def test_usage_new_in_the_window_is_not_a_persistent_anomaly(self):
        self.assertEqual(analyzer([0.0] * 92, [60.0] * 31).leads, [])

    def test_small_spend_is_ignored(self):
        self.assertEqual(analyzer([1.0] * 92, [4.0] * 31).leads, [])


if __name__ == "__main__":
    unittest.main()
