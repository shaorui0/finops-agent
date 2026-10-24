import json
import unittest

from eval.score_visibility import REVIEWED, load, server_catalog
from finops_agent import visibility

SNAP = {"instances": [{"InstanceId": "i-1", "State": {"Name": "running"}}], "nat_gateways": [{"NatGatewayId": "nat-1"}]}
CAT = server_catalog()


def need(terms, scope="running_instances"):
    return {"signal": "s", "concept": "c", "terms": terms, "scope": scope}


class DiscoverTest(unittest.TestCase):
    def names(self, terms, scope="running_instances"):
        label, _ = visibility.expected_scope(scope, {**SNAP}) if not scope.startswith("services") else ("job", None)
        return [c["name"] for c in visibility.discover(need(terms, scope), label, CAT)]

    def test_finds_by_meaning_in_name_or_help(self):
        self.assertEqual(self.names(["cpu", "utilization", "processor"]), ["aws_ec2_cpuutilization_average"])
        self.assertEqual(self.names(["latency", "p99", "percentile"], "services:web,api"), ["http_request_duration_p99_seconds"])
        self.assertEqual(self.names(["nat", "gateway", "traffic"], "nat_gateways"), ["aws_natgateway_bytes_out_to_destination_sum"])

    def test_generic_words_alone_do_not_match_neighbours(self):
        # "utilization percent" is true of CPU too; memory must not be answered with the CPU metric
        self.assertEqual(self.names(["memory", "ram", "utilization", "percent"]), [])

    def test_scope_label_filters_candidates(self):
        self.assertEqual(self.names(["cpu", "utilization"], "nat_gateways"), [])

    def test_nothing_found_gives_a_query_that_matches_nothing(self):
        plan = visibility.ring2([{"id": "a", "decision": "d", "need": [need(["memory", "ram", "swap"])]}], SNAP, CAT)
        self.assertEqual(plan[0]["discovered"], [])
        self.assertIn(visibility.NO_CANDIDATE, plan[0]["query"]["match[]"])

    def test_words_only_need_without_catalog_is_an_error(self):
        with self.assertRaises(ValueError):
            visibility.ring2([{"id": "a", "decision": "d", "need": [need(["cpu", "utilization"])]}], SNAP)


class ReviewedPathUnchangedTest(unittest.TestCase):
    def test_reviewed_plan_has_no_discovery_and_ignores_catalog(self):
        reqs = visibility.ring1(REVIEWED)
        snap = {"instances": [{"InstanceId": "i-1", "State": {"Name": "running"}}], "nat_gateways": [{"NatGatewayId": "nat-1"}]}
        a, b = visibility.ring2(reqs, snap), visibility.ring2(reqs, snap, CAT)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertTrue(all("discovered" not in p for p in a))
        self.assertEqual(a[0]["query"]["match[]"], '{__name__=~"aws_ec2_cpuutilization_average"}')


class Ring4MixTest(unittest.TestCase):
    REQS = [{"id": "s", "decision": "d", "need": [{"signal": "a"}, {"signal": "b"}]}]
    PLAN = [{"id": "s#0", "sli": "s", "signal": "a", "expected": ["x"]}, {"id": "s#1", "sli": "s", "signal": "b", "expected": ["x"]}]

    def res(self, c0, c1):
        mk = lambda i, c: {"id": i, "metric_names": [], "series_count": 0, "covered": c, "query": {"match[]": "q"}}
        return [mk("s#0", c0), mk("s#1", c1)]

    def test_default_is_worst_of_and_has_no_mix_key(self):
        g = visibility.ring4(self.REQS, self.PLAN, self.res(["x"], []))[0]
        self.assertEqual(g["status"], "missing")
        self.assertNotIn("mix", g)

    def test_mix_keeps_covered_needs_visible(self):
        g = visibility.ring4(self.REQS, self.PLAN, self.res(["x"], []), mix=True)[0]
        self.assertEqual((g["status"], g["mix"]), ("partial", {"covered": 1, "partial": 0, "missing": 1}))
        g = visibility.ring4(self.REQS, self.PLAN, self.res([], []), mix=True)[0]
        self.assertEqual(g["status"], "missing")
        g = visibility.ring4(self.REQS, self.PLAN, self.res(["x"], ["x"]), mix=True)[0]
        self.assertEqual(g["status"], "covered")


if __name__ == "__main__":
    unittest.main()
