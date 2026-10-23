import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_rules  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures_sync" / "parent_rules"
ACCT = "1234" + "56789012"
PRIVATE_WORD = "zorkmidcorp"  # fake employer word, injected via a temp .leak_patterns.local


class SyncRulesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.parent = self.tmp / "parent_rules"
        shutil.copytree(FIXTURE, self.parent)
        self.manifest = sync_rules.build_manifest(self.parent)  # baseline = distillation time
        # a repo root with real docs/rules but a private pattern file of our own
        self.root = self.tmp / "repo"
        shutil.copytree(ROOT / "docs", self.root / "docs")
        shutil.copytree(ROOT / "rules", self.root / "rules")
        (self.root / ".leak_patterns.local").write_text("# test\n" + PRIVATE_WORD + "\n")

    def ax(self, name):
        return self.parent / "axioms" / name

    def run_analyze(self):
        return sync_rules.analyze(self.parent, self.root, self.manifest)

    def test_mapping_parsed_from_distillation_doc(self):
        m = sync_rules.parse_mapping(self.root)
        self.assertEqual(m["FA01"], ["V02", "T02"])
        self.assertEqual(m["FA12"], [])
        self.assertEqual(len(m), 13)

    def test_baseline_has_no_proposals(self):
        r = self.run_analyze()
        self.assertEqual((r["updates"], r["candidates"]), ([], []))
        self.assertEqual(len(r["unchanged"]), 15 - 1)  # 14 mapped parent files, A01 is unmapped

    def test_a_changed_mapped_axiom_listed_as_update(self):
        p = self.ax("v02_fixture.md")
        p.write_text(p.read_text() + "\n新增一段母版改进。\n")
        r = self.run_analyze()
        self.assertEqual([(u["project"], u["parent_id"]) for u in r["updates"]], [("FA01", "V02")])
        self.assertIn("FA01 <- 母版 V02", sync_rules.render(r))

    def test_b_new_unmapped_axiom_is_candidate_only(self):
        (self.ax("z99_new_fixture.md")).write_text("# Z99. 新公理\n\n## 1. 核心公理\n\n全新的想法。\n")
        before = {p.name for p in (self.root / "rules/axioms").iterdir()}
        r = self.run_analyze()
        self.assertEqual([c["file"] for c in r["candidates"]], ["z99_new_fixture.md"])
        self.assertEqual(r["updates"], [])
        text = sync_rules.render(r)
        self.assertIn("候选", text)
        self.assertIn("需人工决定", text)
        # nothing was auto-added to the project
        self.assertEqual(before, {p.name for p in (self.root / "rules/axioms").iterdir()})

    def test_c_private_and_public_leaks_flagged_and_not_copied(self):
        secret_path = "/" + "Users" + "/someone/work/secret"
        p = self.ax("t04_fixture.md")
        p.write_text(p.read_text() + "\n在 %s 公司的内部系统 PrivateSys 里。\n" % PRIVATE_WORD)
        q = self.ax("t07_fixture.md")
        q.write_text(q.read_text() + "\n路径 %s 与账号 %s。\n" % (secret_path, ACCT))
        n = self.ax("y01_new_fixture.md")
        n.write_text("# Y01. 新\n\n## 1. 核心公理\n\n来自 %s 的新想法。\n" % PRIVATE_WORD)
        r = self.run_analyze()
        self.assertEqual(r["flagged"], 3)
        text = sync_rules.render(r)
        for secret in (PRIVATE_WORD, secret_path, ACCT, "PrivateSys", "someone"):
            self.assertNotIn(secret, text)
        self.assertIn("已标记，不输出母版内容", text)
        self.assertIn("私有模式 1", text)
        self.assertIn("公开模式", text)

    def test_d_native_axioms_proposed_back(self):
        r = self.run_analyze()
        self.assertEqual([x["project"] for x in r["propose_back"]], ["FA12", "FA13"])
        self.assertIn("回提母版", sync_rules.render(r))

    def test_cli_writes_only_out_and_refuses_protected_dirs(self):
        mf = self.tmp / "m.json"
        mf.write_text(json.dumps(self.manifest))
        out = self.tmp / "proposal.md"
        snap = {p: p.read_bytes() for p in self.parent.rglob("*.md")}
        rules_snap = {p: p.read_bytes() for p in (self.root / "rules").rglob("*.md")}
        rc = sync_rules.main(["--parent", str(self.parent), "--root", str(self.root),
                              "--manifest", str(mf), "--out", str(out)])
        self.assertEqual(rc, 0)
        self.assertIn("FA12", out.read_text())
        self.assertEqual(snap, {p: p.read_bytes() for p in self.parent.rglob("*.md")})
        self.assertEqual(rules_snap, {p: p.read_bytes() for p in (self.root / "rules").rglob("*.md")})
        for bad in (self.parent / "x.md", self.root / "rules" / "x.md"):
            with self.assertRaises(SystemExit):
                sync_rules.main(["--parent", str(self.parent), "--root", str(self.root),
                                 "--manifest", str(mf), "--out", str(bad)])
            self.assertFalse(bad.exists())


if __name__ == "__main__":
    unittest.main()
