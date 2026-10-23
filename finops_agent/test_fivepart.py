"""Five parts per finding (status/spec/diff/runbook/prevention), plans on every run, owner on findings."""
import json
import tempfile
import threading
import unittest
from argparse import Namespace
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from pathlib import Path

from finops_agent import fivepart, prevention
from finops_agent.__main__ import run
from finops_agent.analyze import NO_OWNER
from finops_agent.judge.prompt import TYPES as JUDGE_TYPES
from testenv import aws_server, catalog, metrics_server

HEADINGS = list(fivepart.LABELS.values())          # 现状 期望 差异 处置 预防
DETECTOR_TYPES = {"misattributed_tags", "unattached_volume", "idle_public_ip", "stopped_instance_storage",
                  "orphan_snapshots", "gp2_to_gp3", "savings_plan_underutilized"}


def _serve(handler):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


class Cards(HTMLParser):
    """Collect, per <div class='card finding'>, the text of its <h4> headings."""

    def __init__(self):
        super().__init__()
        self.cards, self._depth, self._h4 = [], [], False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "div":
            if "finding" in (a.get("class") or "").split() and "card" in (a.get("class") or "").split():
                self.cards.append({"id": a.get("id"), "h4": []})
                self._depth.append(1)
            elif self._depth:
                self._depth[-1] += 1
        if tag == "h4" and self._depth:
            self._h4 = True

    def handle_endtag(self, tag):
        if tag == "div" and self._depth:
            self._depth[-1] -= 1
            if self._depth[-1] == 0:
                self._depth.pop()
        if tag == "h4":
            self._h4 = False

    def handle_data(self, data):
        if self._h4 and self.cards:
            self.cards[-1]["h4"].append(data.strip())


class PrevetionTableTest(unittest.TestCase):
    def test_alerts_exist_in_rules_file(self):
        names = prevention.alert_names()
        for t, p in {**prevention.PREVENTION, "default": prevention.DEFAULT}.items():
            self.assertTrue(p["alerts"], t)
            for a in p["alerts"]:
                self.assertIn(a, names, f"{t}: alert {a} is not defined in config/alerts/finops.rules.yml")

    def test_every_finding_type_has_prevention(self):
        for t in DETECTOR_TYPES | set(JUDGE_TYPES) - {"idle_resource", "other_waste"}:
            self.assertIn(t, prevention.PREVENTION, t)

    def test_each_entry_has_controls_and_cadence_from_slo_doc(self):
        for t, p in prevention.PREVENTION.items():
            self.assertTrue(p["controls"], t)
            self.assertIn("docs/FINOPS_SLO.md Cadence", p["cadence"], t)

    def test_field_names_match_testenv_ground_truth(self):
        self.assertEqual(tuple(fivepart.FIELDS), tuple(catalog.FIELDS))
        gt = catalog.ground_truth()["findings"][0]
        for k in fivepart.FIELDS:
            self.assertIn(k, gt)
        self.assertEqual(prevention.render_text("busy_but_useless").splitlines()[-2][:3], "告警：")

    def test_no_process_spawning(self):
        src = Path(fivepart.__file__).read_text()
        for bad in ("subprocess", "os.system", "Popen"):
            self.assertNotIn(bad, src)


class RunTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.aws, aws_url = _serve(aws_server.Handler)
        cls.prom, prom_url = _serve(metrics_server.Handler)
        cls.tmp = tempfile.TemporaryDirectory()
        args = Namespace(aws_endpoint=aws_url, prom=prom_url, region="us-east-1", start="2026-09-01", end="2026-10-01",
                         out=cls.tmp.name, run_id="fp", snapshot=None, state=f"{cls.tmp.name}/state.json", no_state=True)
        cls.out = run(args)
        cls.findings = json.loads((cls.out / "findings.json").read_text())["findings"]
        cls.plans = json.loads((cls.out / "plans.json").read_text())
        cls.parts = json.loads((cls.out / "fivepart.json").read_text())
        cls.html = (cls.out / "report.html").read_text()

    @classmethod
    def tearDownClass(cls):
        cls.aws.shutdown()
        cls.prom.shutdown()
        cls.tmp.cleanup()

    # D4: plans on every run
    def test_plans_for_every_finding_with_savings(self):
        by_finding = {p["finding_id"]: p for p in self.plans["plans"]}
        self.assertTrue(self.plans["dry_run"])
        self.assertFalse(self.plans["executed"])
        self.assertEqual(self.plans["skipped"], [])
        judged = [f for f in self.findings if f["detector"].startswith("judge:") and f["monthly_savings_usd"] > 0]
        self.assertTrue(judged, "judged findings with savings must be in the run")
        for f in self.findings:
            if f["monthly_savings_usd"] > 0:
                p = by_finding.get(f["id"])
                self.assertIsNotNone(p, f"{f['id']} {f['type']} has no plan")
                self.assertIn(p["reversal_cost"], ("none", "low", "medium", "high"))
                self.assertTrue(p["rollback"], f["id"])
                self.assertFalse(p["executable"])

    def test_report_shows_plan_and_nothing_executed(self):
        self.assertIn("本次运行没有执行任何命令", self.html)
        self.assertIn("撤回成本", self.html)
        self.assertIn("回滚", self.html)
        self.assertIn("需人工审批", self.html)

    # owner
    def test_findings_carry_owner(self):
        owners = {f["type"]: f["owner"] for f in self.findings}
        self.assertEqual(owners["stopped_instance_storage"], NO_OWNER)     # legacy-reporting has no owner tag
        self.assertEqual(owners["gp2_to_gp3"], "team-api")
        self.assertEqual(owners["busy_but_useless"], "team-data")          # via the ASG's member instances
        by_finding = {p["finding_id"]: p for p in self.plans["plans"]}
        for f in self.findings:
            self.assertTrue(f["owner"])
            if f["id"] in by_finding:
                self.assertEqual(by_finding[f["id"]]["owner"], f["owner"])

    # D17 report half
    def test_five_headings_per_card_equals_findings(self):
        p = Cards()
        p.feed(self.html)
        self.assertEqual(len(p.cards), len(self.findings))
        self.assertEqual({c["id"] for c in p.cards}, {f["id"] for f in self.findings})
        for c in p.cards:
            self.assertEqual(c["h4"], HEADINGS, c["id"])
        self.assertEqual(sum(len(c["h4"]) for c in p.cards), 5 * len(self.findings))

    def test_all_five_parts_filled(self):
        self.assertEqual([x["finding_id"] for x in self.parts], [f["id"] for f in self.findings])
        for x in self.parts:
            for k in fivepart.FIELDS:
                self.assertTrue(x[k], f"{x['finding_id']} {k}")
            self.assertIsInstance(x["runbook"], list)
            self.assertTrue(x["prevention"].startswith("控制："))
            for a in x["prevention_alerts"]:
                self.assertIn(a, prevention.alert_names())

    def test_numbers_come_from_code_not_llm(self):
        for f, x in zip(self.findings, self.parts):
            if f["monthly_savings_usd"] > 0:
                self.assertIn(fivepart.usd(f["monthly_savings_usd"]), x["diff"], f["id"])
            llm = [e["what"] for e in f["evidence"] if e["source"] == "llm"]
            for text in llm:
                self.assertNotIn(text, x["status"] + x["diff"])

    def test_runbook_is_the_plan_steps(self):
        by_finding = {p["finding_id"]: p for p in self.plans["plans"]}
        for x in self.parts:
            p = by_finding.get(x["finding_id"])
            if p and p["mode"] == "commands":
                for step in p["steps"]:
                    self.assertIn(f"`{step}`", " ".join(x["runbook"]))
                self.assertEqual(x["plan_id"], p["plan_id"])
            if p is None:
                self.assertIsNone(x["plan_id"])


if __name__ == "__main__":
    unittest.main()
