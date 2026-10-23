"""The catalog: five-part ground truth, computed numbers, generated page."""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from testenv import catalog, world

ROOT = Path(__file__).resolve().parent.parent
GT = catalog.ground_truth()
SCEN = catalog.scenario_docs()


def _entries():
    for e in GT["findings"] + GT["traps"]:
        yield e["id"], e
    for sd in SCEN:
        for key, d in sd["scenario"]["expect"]["details"].items():
            yield f'{sd["name"]}:{key}', d


class FivePartsPresent(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(len(GT["findings"]), 12)
        self.assertEqual(len(GT["traps"]), 4)

    def test_every_entry_has_all_five_fields(self):
        n = 0
        for name, e in _entries():
            n += 1
            for f in catalog.FIELDS:
                v = e.get(f)
                self.assertTrue(v, f"{name}: {f} missing or empty")
                if f == "runbook":
                    self.assertIsInstance(v, list, name)
                    self.assertGreaterEqual(len(v), 2, f"{name}: runbook needs ordered steps")
                    self.assertTrue(all(isinstance(x, str) and x.strip() for x in v), name)
                else:
                    self.assertIsInstance(v, str, name)
                    self.assertTrue(v.strip(), f"{name}: {f} blank")
        self.assertGreaterEqual(n, 12 + 4 + 8 + 7)

    def test_scenario_details_cover_every_expectation(self):
        for sd in SCEN:
            ex = sd["scenario"]["expect"]
            keys = [k for st in ("resolved", "new", "regressed", "persisting") for k in ex.get(st, [])]
            self.assertEqual(sorted(keys), sorted(ex["details"]), sd["name"])
            self.assertTrue(sd["scenario"]["story"]["headline"] and sd["scenario"]["story"]["narrative"])
            for key, d in ex["details"].items():
                self.assertIn(d["gt"], {f["id"] for f in GT["findings"]}, key)

    def test_runbook_flags_irreversible_steps(self):
        irrev = re.compile(r"delete-volume|release-address|deregister|终止|删卷|删快照|销毁|注销")
        for name, e in _entries():
            for step in e["runbook"]:
                if irrev.search(step):
                    self.assertTrue("[不可逆]" in step or "[可回滚]" in step, f"{name}: {step}")


class NumbersAreComputed(unittest.TestCase):
    def test_no_literal_money_and_placeholders_resolve(self):
        for sd in [None] + SCEN:
            ctx = catalog.Ctx() if sd is None else catalog.scenario_ctx(sd)
            entries = list(GT["findings"] + GT["traps"]) if sd is None else list(sd["scenario"]["expect"]["details"].values())
            for e in entries:
                for f in catalog.FIELDS:
                    raw = e[f] if isinstance(e[f], str) else "\n".join(e[f])
                    self.assertIsNone(re.search(r"\$\s*\d", raw), f"literal money in {f}: {raw[:60]}")
                    out = catalog.five_parts(e, ctx)[f]
                    out = out if isinstance(out, str) else "\n".join(out)
                    self.assertEqual(catalog.unresolved(out), [], out[:80])

    def test_savings_placeholder_matches_world(self):
        ctx = catalog.Ctx()
        self.assertEqual(catalog.render_text("{sav:GT06}", ctx), "$850 至 $950")
        w = world.load(world.WORLD_FILE)
        s, e = w.period
        orphan = sum(l.unblended for l in w.lines if s <= l.day < e and l.resource_id == "vol-0orph00000000c001")
        self.assertEqual(catalog.render_text("{cost:vol-0orph00000000c001}", ctx), catalog.money(orphan))

    def test_unknown_placeholder_fails_loudly(self):
        with self.assertRaises(KeyError):
            catalog.render_text("{nope:x}", catalog.Ctx())


class AlertsExist(unittest.TestCase):
    def test_alert_references_resolve_to_rules(self):
        known = catalog.alert_names()
        self.assertIn("BusyButUselessFleet", known)
        seen = set()
        for name, e in _entries():
            for a in catalog.ALERT_REF.findall(e["prevention"]):
                seen.add(a)
                self.assertIn(a, known, f"{name}: unknown alert {a}")
        self.assertTrue({"BusyButUselessFleet", "NatBytesSurge", "FinOpsRegression"} <= seen)


class GeneratedPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = catalog.build()

    def test_contains_every_id(self):
        for e in GT["findings"] + GT["traps"]:
            self.assertIn(f'id="{e["id"]}"', self.html)
            self.assertIn(e["id"], self.html)

    def test_contains_scenarios_and_gaps(self):
        for sd in SCEN:
            self.assertIn(sd["name"], self.html)
            for key in sd["scenario"]["expect"]["details"]:
                self.assertIn(key.replace("&", "&amp;"), self.html)
        for g in GT["visibility_gaps"]:
            self.assertIn(g["sli"], self.html)

    def test_self_contained(self):
        self.assertNotRegex(self.html, r"<script|src=\"http|href=\"http|@import")
        self.assertIn("prefers-color-scheme:dark", self.html)
        self.assertIn("viewport", self.html)
        self.assertIn("<svg", self.html)

    def test_five_part_headings_per_card(self):
        n = len(GT["findings"]) + len(GT["traps"]) + sum(len(sd["scenario"]["expect"]["details"]) for sd in SCEN)
        for h in ("现状 status", "期望 spec", "差异 diff", "处置 runbook", "预防 prevention"):
            self.assertEqual(self.html.count(f"<h4>{h}</h4>"), n, h)

    def test_cli_writes_file(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "c.html"
            subprocess.run([sys.executable, "-m", "testenv.catalog", "--out", str(out)], cwd=ROOT, check=True, capture_output=True)
            self.assertEqual(out.read_text(), self.html)


class BaseWorldUnchanged(unittest.TestCase):
    def test_lines_digest_is_stable_and_ground_truth_semantics_kept(self):
        w = world.load(world.WORLD_FILE)
        digest = hashlib.sha256(json.dumps([l.__dict__ for l in w.lines], default=str, sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest, "ebb2c2890fbbf99fe06b3f7e7916cffc5971fdb37f36e98fdde824cff8b35db3")
        f = {x["id"]: x["monthly_savings_usd"] for x in GT["findings"]}
        self.assertEqual(f["GT06"], {"min": 850, "max": 950})


if __name__ == "__main__":
    unittest.main()
