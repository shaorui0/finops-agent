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
                         out=cls.tmp.name, run_id="t", snapshot=None,
                         state=f"{cls.tmp.name}/state.json", no_state=False)
        cls.out = run(args)
        cls.result = json.loads((cls.out / "findings.json").read_text())
        cls.by_type = {f["type"]: f for f in cls.result["findings"]}

    @classmethod
    def tearDownClass(cls):
        cls.aws.shutdown()
        cls.prom.shutdown()
        cls.tmp.cleanup()

    def test_artifacts_written(self):
        for name in ("snapshot.json", "visibility.json", "findings.json", "plans.json", "fivepart.json", "slo.json", "finops_metrics.prom", "trace.jsonl", "report.html"):
            self.assertTrue((self.out / name).exists(), name)

    def test_plans_and_owner_on_every_run(self):
        plans = json.loads((self.out / "plans.json").read_text())
        self.assertEqual(len(plans["plans"]), sum(1 for f in self.result["findings"] if f["monthly_savings_usd"] > 0 or f["method_step"] == "M5_commitment"))
        self.assertTrue(all("owner" in f for f in self.result["findings"]))

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

    def test_slo_reflects_neglected_account(self):
        rows = {r["id"]: r for r in self.result["slo"]["rows"]}
        for sli in ("waste_ratio", "commitment_utilization", "useful_work_ratio", "anomaly_time_to_detect_days", "orphan_max_age_days"):
            self.assertEqual(rows[sli]["status"], "violated", sli)
        self.assertEqual(rows["anomaly_time_to_detect_days"]["value"], 27)
        self.assertEqual(len(self.result["slo"]["diff"]["new"]), len(self.result["findings"]))

    def test_report_shows_not_redetected_in_slo_section(self):
        from finops_agent import report
        run = json.loads(json.dumps(self.result))
        run["trace"] = [json.loads(l) for l in (self.out / "trace.jsonl").read_text().splitlines()]
        run["plans"] = json.loads((self.out / "plans.json").read_text())
        run["fivepart"] = json.loads((self.out / "fivepart.json").read_text())
        self.assertIn("未再检出 <b class=covered>0</b>", report.render(run))
        run["slo"]["diff"]["not_redetected"] = [{"key": "gp2_to_gp3|vol-a", "since": "r1", "why": "vol-a 仍在清单里"}]
        html = report.render(run)
        self.assertIn("未再检出 <b class=partial>1</b>", html)
        self.assertIn("资源仍在，但本次未再检出", html)
        self.assertIn("gp2_to_gp3|vol-a", html)

    def test_trace_is_read_only(self):
        calls = [json.loads(l) for l in (self.out / "trace.jsonl").read_text().splitlines()]
        ops = [c["op"] for c in calls if c["source"] != "llm"]     # LLM calls are traced too, but they are not AWS/Prometheus reads
        self.assertTrue(ops)
        self.assertTrue(all(op.startswith(("describe_", "get_", "/api/v1/")) for op in ops), ops)


if __name__ == "__main__":
    unittest.main()
