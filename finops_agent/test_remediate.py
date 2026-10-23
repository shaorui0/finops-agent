import ast
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from finops_agent import remediate

HERE = os.path.dirname(__file__)
FIX = os.path.join(HERE, "test_remediate_fixture.json")
SRC = os.path.join(HERE, "remediate.py")


def _doc():
    with open(FIX) as fh:
        return json.load(fh)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.doc = _doc()
        self.plans, self.skipped = remediate.build_plans(self.doc)
        self.by_finding = {p.finding_id: p for p in self.plans}

    def test_every_saving_finding_has_plan(self):
        for f in self.doc["findings"]:
            if f["monthly_savings_usd"] > 0:
                self.assertIn(f["id"], self.by_finding, f)
        self.assertEqual(self.skipped, [])

    def test_plan_fields_complete(self):
        for p in self.plans:
            self.assertIn(p.reversal_cost, {"none", "low", "medium", "high"})
            self.assertTrue(p.reversal_reason and p.preconditions and p.evidence and p.owner)
            self.assertFalse(p.executable)
            if p.mode == "commands":
                self.assertTrue(p.steps and p.rollback, p.plan_id)
                self.assertTrue(any(s.startswith(("aws ", "SNAP_ID=$(aws", "AMI_ID=$(aws")) for s in p.steps))

    def test_destructive_steps_preceded_by_backup(self):
        for fid, key in (("F02", "create-snapshot"), ("F04", "create-image")):
            steps = self.by_finding[fid].steps
            idx_backup = next(i for i, s in enumerate(steps) if key in s)
            idx_del = next(i for i, s in enumerate(steps) if "delete-volume" in s or "terminate-instances" in s)
            self.assertLess(idx_backup, idx_del)
        self.assertTrue(any("snapshot" in c for c in self.by_finding["F02"].preconditions))

    def test_irreversible_snapshot_deletion_not_in_commands(self):
        p = self.by_finding["F05"]
        self.assertEqual(p.reversal_cost, "high")
        self.assertFalse(any("delete-snapshot" in s or "deregister-image" in s for s in p.steps))

    def test_commitment_is_advice_only(self):
        p = self.by_finding["F07"]
        self.assertEqual((p.mode, p.reversal_cost, p.steps, p.rollback), ("advice_only", "high", [], []))
        self.assertTrue(p.advice)

    def test_order_delete_downsize_commit(self):
        steps = [p.method_step for p in self.plans]
        self.assertEqual(steps, sorted(steps, key=lambda s: remediate.STEP_ORDER[s]))
        self.assertEqual(steps[0], "M3_delete")
        self.assertEqual(steps[-1], "M5_commitment")

    def test_owner_map(self):
        plans, _ = remediate.build_plans(self.doc, {"vol-0orph00000000c001": "team-x"})
        self.assertEqual({p.finding_id: p for p in plans}["F02"].owner, "team-x")


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.out = os.path.join(self.tmp, "plans.json")

    def run_cli(self, *argv):
        o, e = io.StringIO(), io.StringIO()
        with redirect_stdout(o), redirect_stderr(e):
            rc = remediate.main(list(argv))
        return rc, o.getvalue(), e.getvalue()

    def test_plans_writes_file(self):
        rc, out, _ = self.run_cli("plans", FIX, "--out", self.out)
        self.assertEqual(rc, 0)
        with open(self.out) as fh:
            doc = json.load(fh)
        self.assertTrue(doc["dry_run"])
        self.assertEqual(len(doc["plans"]), 6)
        print(out)

    def test_apply_refuses_without_approve(self):
        self.run_cli("plans", FIX, "--out", self.out)
        rc, out, err = self.run_cli("apply", self.out)
        self.assertEqual(rc, 2)
        self.assertEqual(out, "")
        self.assertIn("--approve", err)

    def test_apply_unknown_and_advice_only_refused(self):
        self.run_cli("plans", FIX, "--out", self.out)
        self.assertEqual(self.run_cli("apply", self.out, "--approve", "P-NOPE")[0], 2)
        rc, out, err = self.run_cli("apply", self.out, "--approve", "P-F07")
        self.assertEqual((rc, out), (2, ""))
        self.assertIn("advice-only", err)

    def test_apply_prints_script_only(self):
        self.run_cli("plans", FIX, "--out", self.out)
        with mock.patch.object(subprocess, "run") as r, mock.patch.object(subprocess, "Popen") as po, \
                mock.patch.object(os, "system") as sy:
            rc, out, _ = self.run_cli("apply", self.out, "--approve", "P-F02")
            path = os.path.join(self.tmp, "x.sh")
            rc2, _, _ = self.run_cli("apply", self.out, "--approve", "P-F02", "--script", path)
        for m in (r, po, sy):
            m.assert_not_called()
        self.assertEqual((rc, rc2), (0, 0))
        self.assertIn("aws ec2 delete-volume", out)
        self.assertIn("#   [ ]", out)
        with open(path) as fh:
            text = fh.read()
        self.assertEqual(text, out)
        self.assertFalse(os.access(path, os.X_OK))


class NoExecutionTests(unittest.TestCase):
    def test_remediate_has_no_exec_capability(self):
        with open(SRC) as fh:
            tree = ast.parse(fh.read())
        banned = {"subprocess", "os", "pty", "shlex", "multiprocessing", "ctypes", "socket", "urllib", "requests", "boto3"}
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                self.assertFalse({a.name.split(".")[0] for a in n.names} & banned, n.names)
            if isinstance(n, ast.ImportFrom):
                self.assertNotIn((n.module or "").split(".")[0], banned)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                self.assertNotIn(n.func.id, {"exec", "eval", "__import__", "compile"})

    def test_commands_are_plain_text(self):
        plans, _ = remediate.build_plans(_doc())
        for p in plans:
            for s in p.steps + p.rollback:
                self.assertIsInstance(s, str)


if __name__ == "__main__":
    unittest.main()
