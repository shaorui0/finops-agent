import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from check_rules import check, check_docs  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


class CheckRulesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()) / "repo"
        shutil.copytree(REPO, self.tmp, ignore=shutil.ignore_patterns(".git", "__pycache__", ".leak_patterns.local"))

    def tearDown(self):
        shutil.rmtree(self.tmp.parent)

    def errors(self):
        return check(self.tmp)

    def test_baseline_passes(self):
        self.assertEqual(self.errors(), [])

    def test_missing_required_file(self):
        (self.tmp / "rules/SOUL.md").unlink()
        self.assertTrue(any("rules/SOUL.md" in e for e in self.errors()))

    def test_dangling_reference(self):
        with open(self.tmp / "CLAUDE.md", "a") as f:
            f.write("\nsee `docs/nope.md`\n")
        self.assertTrue(any("docs/nope.md" in e for e in self.errors()))

    def test_axiom_missing_section(self):
        f = next((self.tmp / "rules/axioms").glob("fa01_*.md"))
        f.write_text(f.read_text().replace("## 本仓库怎么落地", "## x"))
        self.assertTrue(any("本仓库怎么落地" in e for e in self.errors()))

    def test_axiom_not_indexed(self):
        (self.tmp / "rules/axioms/fa99_orphan.md").write_text("# x")
        self.assertTrue(any("fa99_orphan.md not listed" in e for e in self.errors()))

    def test_public_leak(self):
        (self.tmp / "rules/leak.md").write_text("account " + "1234567890" + "12")
        self.assertTrue(any("leak pattern in rules/leak.md" in e for e in self.errors()))

    def test_private_leak_from_local_file(self):
        (self.tmp / ".leak_patterns.local").write_text("acme-corp\n")
        (self.tmp / "rules/leak.md").write_text("we ran this at Acme-Corp")
        self.assertTrue(any("leak pattern in rules/leak.md" in e for e in self.errors()))


class DocsCheckTest(unittest.TestCase):
    """D11 link check and D16 heading-language check, on a tiny fixture repo."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for d in ("docs", "rules", "eval", "openspec/changes/x", "testenv"):
            (self.tmp / d).mkdir(parents=True, exist_ok=True)
        (self.tmp / "eval/score.py").write_text("")
        (self.tmp / "docs/A.md").write_text("# 甲\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def put(self, rel, text):
        (self.tmp / rel).write_text(text)
        return check_docs(self.tmp)

    # D11: links and backticked paths
    def test_links_pass(self):
        ok = ("# 标题\n见 [甲](A.md#x)、[评分](../eval/score.py)、[外](https://example.com/nope.md)、[锚](#上)、"
              "[目录](../eval/)、`eval/score.py`、`eval/score.py:12`、`runs/t1/report.html`、`eval/*.py`、`eval/<x>.py`、"
              "`openspec/changes/x/none.md`。\n```\n[坏](gone.md) `eval/gone.py`\n```\n")
        self.assertEqual(self.put("docs/B.md", ok), [])

    def test_dangling_link_reports_file_and_line(self):
        errs = self.put("docs/B.md", "# 标题\n\n见 [丢](gone.md#a)\n")
        self.assertEqual(len(errs), 1)
        self.assertTrue(errs[0].startswith("docs/B.md:3:") and "gone.md" in errs[0], errs)

    def test_link_is_relative_to_the_file_not_the_root(self):
        errs = self.put("docs/B.md", "# 标题\n[x](eval/score.py)\n")      # resolves from docs/, so it is dangling
        self.assertEqual(len(errs), 1)

    def test_dangling_backticked_path_is_relative_to_root(self):
        errs = self.put("rules/R.md", "# 规则\n`eval/gone.py` 与 `docs/Z.md`\n")
        self.assertEqual(len(errs), 2)
        self.assertTrue(all(e.startswith("rules/R.md:2:") for e in errs), errs)

    def test_only_listed_files_are_checked(self):
        self.assertEqual(self.put("testenv/NOTES.md", "# English Heading\n[x](gone.md)\n"), [])
        self.assertEqual(len(self.put("testenv/README.md", "# 说明\n[x](gone.md)\n")), 1)

    # D16: headings
    def test_headings_pass(self):
        ok = "# 总览\n## 用 `make test` 跑 `pytest suite`\n### SLO 与 FinOps\n## Docker\n#### 第 3 步 run\n```\n# two words here\n```\n"
        self.assertEqual(self.put("docs/B.md", ok), [])

    def test_english_heading_fails_with_line(self):
        errs = self.put("docs/B.md", "# 总览\n\n## Waste budget\n")
        self.assertEqual(len(errs), 1)
        self.assertTrue(errs[0].startswith("docs/B.md:3:") and "Waste budget" in errs[0], errs)

    def test_hyphenated_english_title_fails(self):
        self.assertEqual(len(self.put("README.md", "# finops-agent\n")), 1)


if __name__ == "__main__":
    unittest.main()
