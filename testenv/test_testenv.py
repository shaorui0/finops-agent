"""Round-trip tests: real boto3 / HTTP clients against both test servers."""
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode
from urllib.request import urlopen

import boto3
from botocore.exceptions import ClientError

from testenv import aws_server, metrics_server
from testenv.world import load


def _serve(handler):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


class WorldConsistency(unittest.TestCase):
    """Ground-truth savings ranges must agree with the cost model."""

    def setUp(self):
        self.w = load()
        s, e = self.w.period
        self.lines = [l for l in self.w.lines if s <= l.day < e]

    def total(self, pred):
        return sum(l.unblended for l in self.lines if pred(l))

    def gt(self, gid):
        return next(f for f in self.w.raw["ground_truth"]["findings"] if f["id"] == gid)["monthly_savings_usd"]

    def assertInRange(self, value, gid):
        r = self.gt(gid)
        self.assertTrue(r["min"] <= value <= r["max"], f"{gid}: {value:.2f} not in {r}")

    def test_savings_ranges(self):
        self.assertInRange(self.total(lambda l: l.usage_type == "NatGateway-Bytes"), "GT02")
        self.assertInRange(self.total(lambda l: l.usage_type == "DataTransfer-Regional-Bytes"), "GT03")
        self.assertInRange(self.total(lambda l: l.resource_id == "vol-0leg000000000b001"), "GT06")
        self.assertInRange(self.total(lambda l: l.resource_id == "vol-0orph00000000c001"), "GT09")
        self.assertInRange(self.total(lambda l: l.resource_id == "eipalloc-0aa0000000000001"), "GT10")
        self.assertInRange(self.total(lambda l: l.resource_id == "vol-0db0000000000a001") * 0.2, "GT11")
        etl = self.total(lambda l: l.resource_id == "i-0a1b2c3d4e5f60501" and l.usage_type.startswith("Box"))
        self.assertInRange(etl * 22 / 24, "GT12")

    def test_sp_unused_after_migration(self):
        s, e = self.w.period
        days = sorted({l.day for l in self.lines})
        u = [self.w.sp_utilization(d) for d in days]
        pct = 100 * sum(x["used"] for x in u) / sum(x["total"] for x in u)
        self.assertTrue(55 < pct < 65, pct)

    def test_findings_are_deep_and_labelled(self):
        gt = self.w.raw["ground_truth"]["findings"]
        self.assertTrue(all(f.get("method_step") and f.get("hops") and f.get("evidence_sources") for f in gt))
        self.assertGreaterEqual(sum(len(f["hops"]) >= 3 for f in gt), len(gt) // 2)

    def test_amortized_equals_unblended_in_total(self):
        self.assertAlmostEqual(sum(l.unblended for l in self.lines), sum(l.amortized for l in self.lines), places=4)


class AwsServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, url = _serve(aws_server.Handler)
        kw = dict(endpoint_url=url, region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="x")
        cls.ec2 = boto3.client("ec2", **kw)
        cls.ce = boto3.client("ce", **kw)
        cls.kw = kw

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_ec2_describes(self):
        inst = [i for r in self.ec2.describe_instances()["Reservations"] for i in r["Instances"]]
        self.assertEqual(len(inst), len(load().instances))
        stopped = self.ec2.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}])
        self.assertEqual(len(stopped["Reservations"]), 1)
        vols = self.ec2.describe_volumes()["Volumes"]
        self.assertIn("available", {v["State"] for v in vols})
        self.assertEqual(self.ec2.describe_vpc_endpoints()["VpcEndpoints"], [])
        self.assertGreater(len(self.ec2.describe_snapshots(OwnerIds=["self"])["Snapshots"]), 60)

    def test_cost_explorer(self):
        r = self.ce.get_cost_and_usage(TimePeriod={"Start": "2026-09-01", "End": "2026-10-01"}, Granularity="MONTHLY",
                                       Metrics=["UnblendedCost"], GroupBy=[{"Type": "DIMENSION", "Key": "USAGE_TYPE"}])
        keys = {g["Keys"][0] for g in r["ResultsByTime"][0]["Groups"]}
        self.assertIn("NatGateway-Bytes", keys)
        self.assertIn("DataTransfer-Regional-Bytes", keys)
        with self.assertRaises(ClientError):
            self.ce.get_cost_and_usage_with_resources(TimePeriod={"Start": "2026-09-01", "End": "2026-10-01"}, Granularity="DAILY",
                                                      Metrics=["UnblendedCost"], Filter={"Dimensions": {"Key": "SERVICE", "Values": ["EC2 - Other"]}})

    def test_writes_rejected(self):
        with self.assertRaises(ClientError) as cm:
            self.ec2.terminate_instances(InstanceIds=["i-0a1b2c3d4e5f60101"])
        self.assertEqual(cm.exception.response["Error"]["Code"], "UnauthorizedOperation")

    def test_other_services(self):
        self.assertEqual(boto3.client("sts", **self.kw).get_caller_identity()["Account"], load().account_id)
        asgs = boto3.client("autoscaling", **self.kw).describe_auto_scaling_groups()["AutoScalingGroups"]
        self.assertEqual({a["AutoScalingGroupName"] for a in asgs}, {"web-asg", "ingest-asg"})
        sp = boto3.client("savingsplans", **self.kw).describe_savings_plans()["savingsPlans"]
        self.assertEqual(sp[0]["ec2InstanceFamily"], "m5")


class MetricsServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.url = _serve(metrics_server.Handler)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def q(self, query, time="2026-09-30T12:00:00Z"):
        with urlopen(f"{self.url}/api/v1/query?{urlencode({'query': query, 'time': time})}") as r:
            return json.load(r)

    def test_retry_storm_visible_only_in_app_metrics(self):
        cpu = float(self.q('avg(avg_over_time(aws_ec2_cpuutilization_average{instance_id=~"i-0a1b2c3d4e5f6040."}[1d]))')["data"]["result"][0]["value"][1])
        self.assertGreater(cpu, 50)
        res = {r["metric"]["status"]: float(r["value"][1]) for r in self.q("sum by (status) (increase(ingest_jobs_total[1d]))")["data"]["result"]}
        self.assertEqual(res["succeeded"], 0.0)

    def test_tidal_trap(self):
        avg = float(self.q('avg(avg_over_time(aws_ec2_cpuutilization_average{instance_id=~"i-0a1b2c3d4e5f6010."}[30d]))')["data"]["result"][0]["value"][1])
        p95 = float(self.q('max(quantile_over_time(0.95, aws_ec2_cpuutilization_average{instance_id=~"i-0a1b2c3d4e5f6010."}[30d]))')["data"]["result"][0]["value"][1])
        self.assertLess(avg, 35)
        self.assertGreater(p95, 65)

    def test_no_memory_metric(self):
        with urlopen(f"{self.url}/api/v1/label/__name__/values") as r:
            names = json.load(r)["data"]
        self.assertFalse(any("mem" in n for n in names))

    def test_unsupported_query_is_bad_data(self):
        try:
            urlopen(f"{self.url}/api/v1/query?{urlencode({'query': 'histogram_quantile(0.9, x)'})}")
            self.fail("expected HTTP 400")
        except Exception as e:
            self.assertEqual(json.load(e)["errorType"], "bad_data")


if __name__ == "__main__":
    unittest.main()
