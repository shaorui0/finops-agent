#!/usr/bin/env python3
"""Compare the private parent workspace's axioms with this repo's distilled ones
and print a PROPOSAL (Chinese markdown) for a human to review.

Never applies anything: it reads the parent and this repo, writes only the
proposal to --out (or stdout), and refuses an --out inside either rules/ tree.

Change detection: tools/rules_sync_manifest.json stores filename + sha256 of every
parent axiom file at distillation time (no content). A mapped parent file whose hash
differs is "changed"; a parent file absent from the manifest is "new".

Mapping comes from the table under "选了哪些公理" in docs/DISTILLATION.md.

Leak safety: if a parent file matches a leak pattern (public ones from
tools/check_rules.py + `.leak_patterns.local`), it is flagged and none of its text
is emitted.

Usage:
  python3 tools/sync_rules.py --parent <parent>/rules [--out proposal.md]
  python3 tools/sync_rules.py --parent <parent>/rules --init-manifest   # record baseline
"""
import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Path(__file__).resolve().parent / "rules_sync_manifest.json"
EXCERPT_CHARS = 300


def _load_check_rules():
    spec = importlib.util.spec_from_file_location("check_rules", Path(__file__).resolve().parent / "check_rules.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parent_axiom_files(parent):
    d = Path(parent) / "axioms"
    return sorted(p for p in d.glob("*.md") if p.name != "INDEX.md")


def build_manifest(parent):
    return {"version": 1, "axioms": {p.name: sha256(p) for p in parent_axiom_files(parent)}}


def parse_mapping(root):
    """{'FA01': ['V02', 'T02'], ...}; native axioms map to []."""
    text = (Path(root) / "docs/DISTILLATION.md").read_text()
    sec = text.split("## 选了哪些公理", 1)[1].split("\n## ", 1)[0]
    mapping = {}
    for line in sec.splitlines():
        m = re.match(r"\|\s*(FA\d+)\s[^|]*\|\s*([^|]+?)\s*\|", line)
        if m:
            mapping[m.group(1)] = re.findall(r"[A-Z]\d{2}", m.group(2))
    return mapping


def project_axioms(root):
    """{'FA12': {'file': name, 'native': bool}}"""
    out = {}
    for p in sorted((Path(root) / "rules/axioms").glob("fa*.md")):
        text = p.read_text()
        fid = p.name[:4].upper()
        src = text.split("## 来源", 1)[1] if "## 来源" in text else ""
        out[fid] = {"file": p.name, "native": "项目原生" in src}
    return out


def find_parent_file(parent, pid):
    hits = [p for p in parent_axiom_files(parent) if p.name.lower().startswith(pid.lower() + "_")]
    return hits[0] if hits else None


def scan_leaks(text, patterns):
    """Return labels only (never the matched text)."""
    labels = []
    for i, p in enumerate(patterns):
        if any(len(set(m.group())) > 1 for m in p.finditer(text)):
            labels.append("公开模式 %d" % (i + 1) if i < _N_PUBLIC else "私有模式 %d" % (i + 1 - _N_PUBLIC))
    return labels


_N_PUBLIC = len(_load_check_rules().PUBLIC_LEAKS)


def excerpt(text):
    title = next((l.lstrip("# ").strip() for l in text.splitlines() if l.startswith("#")), "")
    body = re.sub(r"^---.*?---", "", text, flags=re.S)
    m = re.search(r"##\s*1?\.?\s*核心公理\s*\n+(.+?)(?:\n\n|\Z)", body, flags=re.S)
    core = (m.group(1) if m else "").strip().replace("\n", " ")
    return title, core[:EXCERPT_CHARS]


def analyze(parent, root=ROOT, manifest=None):
    root, parent = Path(root), Path(parent)
    manifest = manifest if manifest is not None else json.loads(MANIFEST.read_text())
    known = manifest["axioms"]
    patterns = _load_check_rules().leak_patterns(root)
    mapping = parse_mapping(root)
    proj = project_axioms(root)

    res = {"updates": [], "candidates": [], "propose_back": [], "unchanged": [], "missing": [], "flagged": 0}

    def record(kind, item, path):
        text = path.read_text()
        labels = scan_leaks(text, patterns)
        item["flags"] = labels
        if labels:
            res["flagged"] += 1
        else:
            item["title"], item["excerpt"] = excerpt(text)
        res[kind].append(item)

    mapped_files = set()
    for fid, pids in mapping.items():
        if fid not in proj:
            continue
        for pid in pids:
            f = find_parent_file(parent, pid)
            if f is None:
                res["missing"].append({"project": fid, "parent_id": pid})
                continue
            mapped_files.add(f.name)
            if known.get(f.name) == sha256(f):
                res["unchanged"].append({"project": fid, "parent_id": pid, "file": f.name})
            else:
                record("updates", {"project": fid, "parent_id": pid, "file": f.name,
                                   "baseline": f.name in known}, f)
    for f in parent_axiom_files(parent):
        if f.name not in known and f.name not in mapped_files:
            record("candidates", {"file": f.name}, f)
    for fid, info in proj.items():
        if info["native"]:
            res["propose_back"].append({"project": fid, "file": info["file"]})
    return res


def render(res):
    L = ["# 规则同步提议（仅供人工审阅，未应用任何改动）", ""]
    L += ["摘要：母版已变更且已映射 %d 条；母版新增未映射 %d 条（候选）；项目原生可回提 %d 条；"
          "未变化 %d 条；映射缺失 %d 条；命中泄漏模式被标记 %d 条。"
          % (len(res["updates"]), len(res["candidates"]), len(res["propose_back"]),
             len(res["unchanged"]), len(res["missing"]), res["flagged"]), ""]

    def entry(it):
        if it["flags"]:
            return ["  - **已标记，不输出母版内容**：命中 " + "、".join(it["flags"]) + "。需人工在母版中脱敏后再改写。"]
        out = ["  - 母版标题：" + it["title"]]
        if it["excerpt"]:
            out.append("  - 核心公理摘录（前 %d 字）：%s" % (EXCERPT_CHARS, it["excerpt"]))
        return out

    L += ["## 1. 母版公理已变更，建议更新本仓库对应公理", ""]
    for it in res["updates"] or []:
        L.append("- %s <- 母版 %s（`%s`）" % (it["project"], it["parent_id"], it["file"]))
        L += entry(it)
    if not res["updates"]:
        L.append("（无）")
    L += ["", "## 2. 候选：母版新增、未映射，需人工决定", "",
          "不会自动加入；是否与 FinOps 相关、如何改写，由维护者判断。", ""]
    for it in res["candidates"]:
        L.append("- `%s`" % it["file"])
        L += entry(it)
    if not res["candidates"]:
        L.append("（无）")
    L += ["", "## 3. 项目原生公理，建议回提母版", ""]
    for it in res["propose_back"]:
        L.append("- %s（`rules/axioms/%s`）：来源标注为项目原生，母版没有对应条目" % (it["project"], it["file"]))
    if not res["propose_back"]:
        L.append("（无）")
    if res["missing"]:
        L += ["", "## 4. 映射缺失", ""]
        L += ["- %s 映射的母版 %s 在母版中找不到文件" % (m["project"], m["parent_id"]) for m in res["missing"]]
    return "\n".join(L) + "\n"


def refuse_if_protected(out, parent, root):
    out = Path(out).resolve()
    for guard in (Path(parent).resolve(), (Path(root) / "rules").resolve()):
        if out == guard or guard in out.parents:
            raise SystemExit("refusing to write proposal inside %s" % guard)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--parent", required=True, help="parent workspace rules/ directory (read-only)")
    ap.add_argument("--out", help="write proposal here (default: stdout)")
    ap.add_argument("--manifest", default=str(MANIFEST))
    ap.add_argument("--root", default=str(ROOT), help="this repo (for mapping, axioms, leak patterns)")
    ap.add_argument("--init-manifest", action="store_true", help="record parent axiom hashes as the baseline")
    a = ap.parse_args(argv)

    if a.init_manifest:
        refuse_if_protected(a.manifest, a.parent, a.root)
        Path(a.manifest).write_text(json.dumps(build_manifest(a.parent), indent=1, sort_keys=True) + "\n")
        print("manifest: %d files -> %s" % (len(build_manifest(a.parent)["axioms"]), a.manifest))
        return 0
    res = analyze(a.parent, a.root, json.loads(Path(a.manifest).read_text()))
    text = render(res)
    if a.out:
        refuse_if_protected(a.out, a.parent, a.root)
        Path(a.out).write_text(text)
        print("proposal written: %s" % a.out)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
