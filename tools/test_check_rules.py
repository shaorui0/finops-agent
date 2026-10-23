import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from check_rules import check  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


class CheckRulesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for rel in ["CLAUDE.md", "AGENTS.md", "rules", "hooks", "tools"]:
            src = REPO / rel
            if src.is_dir():
                shutil.copytree(src, self.tmp / rel, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy(src, self.tmp / rel)
        for rel in ["docs/REQUIREMENTS.md", "docs/aws_account_hardening.md", "docs/DISTILLATION.md"]:
            (self.tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO / rel, self.tmp / rel)
        for d in ["openspec/specs", "openspec/changes", "reports", "notes/blog", ".claude/skills"]:
            (self.tmp / d).mkdir(parents=True, exist_ok=True)
        (self.tmp / ".claude/settings.json").write_text("{}")

    def tearDown(self):
        shutil.rmtree(self.tmp)

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


if __name__ == "__main__":
    unittest.main()
