"""reports/index.html: every link resolves, diagrams are rendered from their current source, every change is listed."""
import hashlib
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_index  # noqa: E402

INDEX = ROOT / "reports" / "index.html"
DIAG = ROOT / "docs" / "diagrams"
NAMES = [n for n, _, _ in build_index.DIAGRAMS]


class Refs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.ids, self.tags = [], set(), set()

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag)
        for k, v in attrs:
            if k in ("href", "src") and v:
                self.refs.append(v)
            if k == "id" and v:
                self.ids.add(v)


def parse():
    p = Refs()
    p.feed(INDEX.read_text(encoding="utf-8"))
    return p


class IndexTest(unittest.TestCase):
    def test_index_exists_and_is_self_contained(self):
        p = parse()
        self.assertNotIn("script", p.tags)
        for r in p.refs:
            self.assertFalse(re.match(r"^(https?:)?//", r), f"external reference {r}")

    def test_every_link_resolves(self):
        p = parse()
        self.assertGreater(len(p.refs), 40)
        for r in p.refs:
            path, _, frag = r.partition("#")
            if not path:
                self.assertIn(frag, p.ids, f"anchor #{frag} has no target")
                continue
            self.assertTrue((INDEX.parent / path).resolve().exists(), f"broken link {r}")

    def test_diagrams_exist_and_match_source(self):
        readme = (DIAG / "README.md").read_text(encoding="utf-8")
        self.assertEqual(len(NAMES), 6)
        for n in NAMES:
            mmd, svg = DIAG / f"{n}.mmd", DIAG / f"{n}.svg"
            self.assertTrue(mmd.stat().st_size > 0, n)
            self.assertTrue(svg.stat().st_size > 1000, n)
            sha = hashlib.sha256(mmd.read_bytes()).hexdigest()
            # a checkout does not preserve mtimes, so the recorded sha of the source is the durable check
            self.assertTrue(svg.stat().st_mtime >= mmd.stat().st_mtime or sha in readme,
                            f"{n}.svg is older than {n}.mmd and README has no sha {sha[:12]} (re-render and update README)")
            self.assertIn(sha, readme, f"README sha for {n}.mmd is stale")
            self.assertIn(f'id="d-{n}"', INDEX.read_text(encoding="utf-8"), f"{n} not inlined")

    def test_index_lists_every_change(self):
        text = INDEX.read_text(encoding="utf-8")
        for d in (ROOT / "openspec" / "changes").iterdir():
            if d.is_dir() and d.name != "archive":
                self.assertIn(d.name, text, f"{d.name} missing from index")

    def test_key_evidence_pages_linked(self):
        refs = parse().refs
        for want in ("0016-demo-run.html", "testenv-catalog.html", "savings-verification.html",
                     "../eval/EXPERIMENTS.md", "../docs/FINOPS_SLO.md", "../docs/METHOD.md"):
            self.assertIn(want, refs)

    def test_first_sentence(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "proposal.md"
            f.write_text("# x\n\n## Why\n\n第一句。第二句。\n\n## What\nz\n")
            self.assertEqual(build_index.first_sentence(f), "第一句。")

    def test_build_is_deterministic_without_heldout(self):
        self.assertEqual(build_index.build(False), build_index.build(False))


if __name__ == "__main__":
    unittest.main()
