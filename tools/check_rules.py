#!/usr/bin/env python3
"""Self-check for the rules layer and public safety of the repository.

Checks:
  1. required rules files exist
  2. every backticked repo path in CLAUDE.md / AGENTS.md / rules/WORKSPACE.md exists
  3. every axiom file has the four required sections
  4. rules/axioms/INDEX.md and the axiom files list each other
  5. no leak patterns anywhere in tracked-or-new files
  With --docs (also 6 and 7, run over README.md, CONTRIBUTING.md, docs/**, rules/**, testenv/README.md, eval/EXPERIMENTS.md):
  6. every relative markdown link and every backticked repo path resolves (D11)
  7. every heading is Chinese-led: >= 2 ASCII words of >= 2 letters and no CJK character fails (D16)

Leak patterns = generic public ones below + private ones from
`.leak_patterns.local` (one regex per line, gitignored, so the repo never
contains the words it guards against).

Exit 0 = pass, 1 = fail. Usage: python3 tools/check_rules.py [--docs] [repo_root]
"""
import re
import subprocess
import sys
from pathlib import Path

REQUIRED = [
    "rules/SOUL.md",
    "rules/USER.md",
    "rules/COMMUNICATION.md",
    "rules/WORKSPACE.md",
    "rules/axioms/INDEX.md",
    "rules/skills/INDEX.md",
    "CLAUDE.md",
    "AGENTS.md",
]
REF_FILES = ["CLAUDE.md", "AGENTS.md", "rules/WORKSPACE.md"]
AXIOM_SECTIONS = ["## 公理", "## 在 FinOps 里", "## 本仓库怎么落地", "## 来源"]
PUBLIC_LEAKS = [
    r"(?<![\w.-])\d{12}(?![\w.])",  # AWS account id (all-same-digit placeholders are allowed)
    r"AKIA[0-9A-Z]{16}",           # AWS access key id
    r"/Users/[A-Za-z0-9_.-]+/",    # local home paths
]
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}
TEXT_EXT = {".md", ".py", ".json", ".yaml", ".yml", ".html", ".txt", ".sh", ".toml", ""}
PATH_RE = re.compile(r"`([A-Za-z0-9_.][A-Za-z0-9_./<>-]*)`")


def leak_patterns(root):
    pats = list(PUBLIC_LEAKS)
    local = root / ".leak_patterns.local"
    if local.exists():
        pats += [l.strip() for l in local.read_text().splitlines() if l.strip() and not l.startswith("#")]
    return [re.compile(p, re.IGNORECASE) for p in pats]


def repo_files(root):
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=root, capture_output=True, text=True, check=True,
        ).stdout.split()
        return [root / p for p in out]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [p for p in root.rglob("*") if p.is_file() and not SKIP_DIRS & set(p.parts)]


def check(root):
    errors = []
    for rel in REQUIRED:
        if not (root / rel).exists():
            errors.append(f"missing required file: {rel}")

    for rel in REF_FILES:
        f = root / rel
        if not f.exists():
            continue
        for ref in PATH_RE.findall(f.read_text()):
            if "/" not in ref or "<" in ref or ref.startswith("."):
                continue
            if not (root / ref.rstrip("/")).exists():
                errors.append(f"{rel}: dangling reference `{ref}`")

    ax_dir = root / "rules/axioms"
    index = ax_dir / "INDEX.md"
    if index.exists():
        listed = set(re.findall(r"\]\(([^)]+\.md)\)", index.read_text()))
        files = {p.name for p in ax_dir.glob("*.md") if p.name != "INDEX.md"}
        for name in sorted(listed - files):
            errors.append(f"axioms/INDEX.md lists missing file {name}")
        for name in sorted(files - listed):
            errors.append(f"axiom {name} not listed in INDEX.md")
        for name in sorted(files):
            text = (ax_dir / name).read_text()
            for sec in AXIOM_SECTIONS:
                if sec not in text:
                    errors.append(f"axiom {name} missing section '{sec}'")

    pats = leak_patterns(root)
    for f in repo_files(root):
        if f.suffix not in TEXT_EXT or not f.is_file() or f.name == ".leak_patterns.local":
            continue
        try:
            text = f.read_text()
        except UnicodeDecodeError:
            continue
        for p in pats:
            m = next((m for m in p.finditer(text) if len(set(m.group())) > 1), None)
            if m:
                line = text.count("\n", 0, m.start()) + 1
                errors.append(f"leak pattern in {f.relative_to(root)}:{line}")
    return errors


DOC_FILES = ["README.md", "CONTRIBUTING.md", "testenv/README.md", "eval/EXPERIMENTS.md"]
DOC_GLOBS = ["docs/**/*.md", "rules/**/*.md"]
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)|!\[[^\]]*\]\(([^)\s]+)\)")
TICK_RE = re.compile(r"`([^`\n]+)`")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
CJK_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]")
FILE_EXT = re.compile(r"\.(md|py|sh|ya?ml|jsonl?|html|svg|mmd|txt|toml|prom|png|cfg|ini|csv)$")


def doc_files(root):
    found = {root / f for f in DOC_FILES if (root / f).is_file()}
    for g in DOC_GLOBS:
        found |= {p for p in root.glob(g) if p.is_file()}
    return sorted(found)


def doc_lines(text):
    """(line number, line) for every line outside fenced code blocks."""
    fence = None
    for n, line in enumerate(text.splitlines(), 1):
        m = re.match(r"\s*(```+|~~~+)", line)
        if m:
            if fence is None:
                fence = m.group(1)[0]
            elif m.group(1)[0] == fence:
                fence = None
            continue
        if fence is None:
            yield n, line


def _skip_target(t):
    return (re.match(r"[a-z][a-z0-9+.-]*:", t, re.I) is not None or t.startswith(("#", "/", "runs/", "../runs/"))
            or any(c in t for c in "<>*{}$") or t.startswith("openspec/"))


def _repo_path_like(root, ref):
    """A backticked token that names a repo path: has a slash, no spaces, and a known top-level dir or a file extension."""
    if "/" not in ref or " " in ref or ref.startswith(("/", "~", "./", "../")):
        return False
    return (root / ref.split("/")[0]).exists() or bool(FILE_EXT.search(ref.rstrip("/")))


def check_docs(root):
    errors = []
    for f in doc_files(root):
        rel = f.relative_to(root)
        for n, line in doc_lines(f.read_text()):
            for m in LINK_RE.finditer(line):
                t = (m.group(1) or m.group(2)).split("#")[0]
                if not t or _skip_target(m.group(1) or m.group(2)):
                    continue
                if not (f.parent / t.rstrip("/")).exists():
                    errors.append(f"{rel}:{n}: dangling link ({t})")
            for m in TICK_RE.finditer(line):
                ref = re.sub(r"(::\w+|:\d+(-\d+)?|#.*)$", "", m.group(1))
                if _skip_target(ref) or not _repo_path_like(root, ref):
                    continue
                if not (root / ref.rstrip("/")).exists():
                    errors.append(f"{rel}:{n}: dangling path `{ref}`")
            h = HEADING_RE.match(line)
            if h:
                title = TICK_RE.sub("", h.group(1))
                if not CJK_RE.search(title) and len(re.findall(r"[A-Za-z]{2,}", title)) >= 2:
                    errors.append(f"{rel}:{n}: heading not in Chinese ({h.group(1)})")
    return errors


def main():
    argv = sys.argv[1:]
    docs = "--docs" in argv
    argv = [a for a in argv if a != "--docs"]
    root = Path(argv[0] if argv else Path(__file__).resolve().parent.parent)
    errors = check(root) + (check_docs(root) if docs else [])
    for e in errors:
        print(f"FAIL {e}")
    if not errors:
        print("check_rules: OK")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
