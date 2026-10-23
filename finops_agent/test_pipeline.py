"""End-to-end: both test servers in-process, one full run, assertions on the output."""
import json
import tempfile
import threading
import unittest
from argparse import Namespace
from http.server import ThreadingHTTPServer
from pathlib import Path

from finops_agent.__main__ import run
from testenv import aws_server, metrics_server


def _serve(handler):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.aws, aws_url = _serve(aws_server.Handler)
        cls.prom, prom_url = _serve(metrics_server.Handler)
        cls.tmp = tempfile.TemporaryDirectory()
        args = Namespace(aws_endpoint=aws_url, prom=prom_url, region="us-east-1", start="2026-09-01", end="2026-10-01",
                         out=cls.tmp.name, run_id="t", snapshot=None)
        cls.out = run(args)
        cls.result = json.loads((cls.out / "findings.json").read_text())
        cls.by_type = {f["type"]: f for f in cls.result["findings"]}

    @classmethod
    def tearDownClass(cls):
        cls.aws.shutdown()
        cls.prom.shutdown()
        cls.tmp.cleanup()

    def test_artifacts_written(self):
        for name in ("snapshot.json", "visibility.json", "findings.json", "trace.jsonl", "report.html"):
            self.assertTrue((self.out / name).exists(), name)

    def test_invariants_pass(self):
        self.assertEqual(self.result["invariants"], [])

    def test_every_finding_has_method_step_and_evidence(self):
        for f in self.result["findings"]:
            self.assertTrue(f["method_step"].startswith("M"))
            self.assertTrue(f["evidence"])

    def test_two_hop_findings(self):
        f = self.by_type["stopped_instance_storage"]
        self.assertIn("vol-0leg000000000b001", f["resources"])
        self.assertAlmostEqual(f["monthly_savings_usd"], 900, delta=1)
        self.assertIn("savings_plan_underutilized", self.by_type)

    def test_misattribution_found_despite_injection(self):
        self.assertIn("i-0a1b2c3d4e5f60501", self.by_type["misattributed_tags"]["resources"])

    def test_traps_not_flagged(self):
        flagged = {r for f in self.result["findings"] for r in f["resources"]}
        for trap in ("web-asg", "i-0a1b2c3d4e5f60701", "ami-ingest-v7", "ami-web-v12",
                     "i-0a1b2c3d4e5f60101", "i-0a1b2c3d4e5f60102"):
            self.assertNotIn(trap, flagged)

    def test_leads_point_at_deep_findings(self):
        signals = " ".join(l["signal"] for l in self.result["leads"])
        self.assertIn("NatGateway-Bytes", signals)
        self.assertIn("DataTransfer-Regional-Bytes", signals)
        self.assertIn("ingest-asg", signals)

    def test_visibility_gaps_match_planted(self):
        gaps = {g["sli"]: g["status"] for g in self.result["visibility"]["gaps"]}
        self.assertEqual(gaps["rightsizing_headroom"], "missing")
        self.assertEqual(gaps["unit_cost_per_job"], "missing")
        self.assertEqual(gaps["cross_az_attribution"], "partial")
        self.assertEqual(gaps["idle_detection"], "covered")

    def test_trace_is_read_only(self):
        ops = [json.loads(l)["op"] for l in (self.out / "trace.jsonl").read_text().splitlines()]
        self.assertTrue(ops)
        self.assertTrue(all(op.startswith(("describe_", "get_", "/api/v1/")) for op in ops), ops)


if __name__ == "__main__":
    unittest.main()
