#!/usr/bin/env python3
"""Self-check for the rules layer and public safety of the repository.

Checks:
  1. required rules files exist
  2. every backticked repo path in CLAUDE.md / AGENTS.md / rules/WORKSPACE.md exists
  3. every axiom file has the four required sections
  4. rules/axioms/INDEX.md and the axiom files list each other
  5. no leak patterns anywhere in tracked-or-new files

Leak patterns = generic public ones below + private ones from
`.leak_patterns.local` (one regex per line, gitignored, so the repo never
contains the words it guards against).

Exit 0 = pass, 1 = fail. Usage: python3 tools/check_rules.py [repo_root]
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
    r"(?<![\d.])\d{12}(?![\d.])",  # AWS account id
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
            m = p.search(text)
            if m:
                line = text.count("\n", 0, m.start()) + 1
                errors.append(f"leak pattern in {f.relative_to(root)}:{line}")
    return errors


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
    errors = check(root)
    for e in errors:
        print(f"FAIL {e}")
    if not errors:
        print("check_rules: OK")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
