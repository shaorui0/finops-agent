#!/usr/bin/env python3
"""Build reports/index.html: the guided entry page for a human reader.

    python3 tools/build_index.py                 # also runs `python3 -m eval.heldout` (replay, ~10 s) for the metrics table
    python3 tools/build_index.py --no-heldout    # metrics from eval/baseline.json only (used by tests)

Everything on the page is derived from files in the repo: openspec/changes/*/proposal.md (first sentence of "## Why"),
reports/<NNNN>-*.html, notes/blog/<NNNN>-*.md, docs/diagrams/*.svg (inlined), eval/baseline.json, and the
eval.heldout table. The page is one self-contained file: inline CSS and SVG, no JavaScript, no external resources.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "index.html"

DIAGRAMS = [
    ("architecture", "架构：模块与分层",
     "从采集到报告的主流水线，以及它外面的三层只读护栏、eval 和测试环境。"),
    ("dataflow", "数据流：产物谁写谁读",
     "一次运行写出的每个文件、写它的模块、读它的模块，以及跨运行的 state.json。"),
    ("visibility-chain", "可见性链：环 1 到环 4",
     "目标先行：先写需要看到什么，再去系统里找，差集就是缺口。"),
    ("method", "方法：M0 到 M6",
     "运营级与架构级两个层级，以及先删、再降、最后买的顺序。"),
    ("rot-lifecycle", "腐烂：发现的生命周期与巡检节奏",
     "new、persisting、resolved、regressed 四个状态，每日/每周/每月节奏，和对应告警。"),
    ("harness-layers", "Harness：规则、护栏、改动闭环、闸门",
     "把 agent 约束住并让它变好的那一层：规则层、hook、OpenSpec 循环、eval 闸门、CI、写操作 gate。"),
]

EVIDENCE = [
    ("reports/0016-demo-run.html", "最新一次完整运行的报告",
     "对着合成账号跑一遍：发现卡片带五段式（现状、期望、差异、处置、预防）、处置计划、SLO 表。"),
    ("reports/testenv-catalog.html", "测试账号标准答案目录",
     "每个 ground-truth 案例和每个场景变化，都按五段式展开，数字由代码解析。"),
    ("reports/savings-verification.html", "节省核实",
     "resolved 的发现真的让账单少了钱吗：预测、反事实基线、实现节省、账单精确分解。"),
    ("eval/EXPERIMENTS.md", "实验记录",
     "对抗注入、留出世界、环 1 推导等实验的设计、数字和结论。"),
    ("docs/FINOPS_SLO.md", "FinOps SLO",
     "什么叫成本健康：SLI、预算、燃烧速度告警、腐烂、巡检节奏。"),
    ("docs/METHOD.md", "成本优化方法",
     "M0 到 M6 与判断时的硬规则。"),
]

READ_PATH = [
    ("2 分钟", "../README.md", "README：「我怎么思考这个 agent」那张表", "每个设计决定对应一个问题和一个回答。"),
    ("2 分钟", "#diagrams", "本页的架构图和数据流图", "先有全局：一条流水线，三层护栏，产物长什么样。"),
    ("2 分钟", "0016-demo-run.html", "最新 demo 报告", "看一条发现从证据到处置计划是什么样子。"),
    ("1 分钟", "../docs/METHOD.md", "METHOD：M0 到 M6", "为什么先删再降最后买；为什么潮汐不是浪费。"),
    ("1 分钟", "testenv-catalog.html", "测试账号目录", "标准答案和陷阱怎么设计，难度从哪来。"),
    ("1 分钟", "savings-verification.html", "节省核实", "清理见效是账单上的数字，不是叙述。"),
    ("1 分钟", "#changes", "改动一览表", "每个 change 的动机一句话，点进去看报告和笔记。"),
]

CSS = """
:root{--bg:#fafaf7;--fg:#1d1d1b;--mut:#62625c;--card:#fff;--line:#dcdcd2;--acc:#0b5cad;--acc2:#e8f0fa;--ok:#1a7f37;--panel:#fff}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#15161a;--fg:#e6e6e0;--mut:#a0a09a;--card:#1d1f25;--line:#34363f;--acc:#7db4f0;--acc2:#1f2b3a;--ok:#56d364;--panel:#fff}}
:root[data-theme=dark]{--bg:#15161a;--fg:#e6e6e0;--mut:#a0a09a;--card:#1d1f25;--line:#34363f;--acc:#7db4f0;--acc2:#1f2b3a;--ok:#56d364;--panel:#fff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.65 -apple-system,"PingFang SC","Noto Sans SC","Segoe UI",sans-serif}
main{max-width:1040px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:1.9rem;margin:.2em 0}h2{font-size:1.35rem;margin:2em 0 .6em;padding-top:.4em;border-top:1px solid var(--line)}
h3{font-size:1.05rem;margin:1.4em 0 .3em}
a{color:var(--acc)}code{font:.88em ui-monospace,Menlo,monospace;background:var(--acc2);padding:.05em .35em;border-radius:4px}
.lead{color:var(--mut);margin:0 0 1em}
.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media (max-width:720px){.two{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 16px}
.card h3{margin-top:.2em}
nav.toc{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
nav.toc a{border:1px solid var(--line);border-radius:999px;padding:2px 12px;text-decoration:none;background:var(--card);font-size:.9rem}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;background:var(--card);font-size:.92rem}
th,td{border:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top}
th{background:var(--acc2)}
td.n{white-space:nowrap}
figure{margin:1.2em 0}figcaption{color:var(--mut);font-size:.92rem;margin-top:.3em}
.diagram{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px;overflow-x:auto}
.diagram svg{display:block;max-width:100%;height:auto;min-width:640px;margin:0 auto}
.diagram svg foreignObject{overflow:visible}
.src{font-size:.85rem;color:var(--mut)}
ol.path{padding-left:1.2em}ol.path li{margin:.4em 0}
.t{color:var(--mut);font-size:.85rem;margin-right:.4em}
"""


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def first_sentence(proposal: Path) -> str:
    text = proposal.read_text(encoding="utf-8")
    m = re.search(r"^## Why\s*\n+(.*?)(?=\n## |\Z)", text, re.S | re.M)
    if not m:
        return "(proposal 没有 Why 小节)"
    para = m.group(1).strip().split("\n\n")[0].replace("\n", " ")
    cut = re.search(r"。|\.(?=\s|$)", para)
    return para[: cut.end()] if cut else para


def inline_svg(name: str) -> str:
    svg = (ROOT / "docs" / "diagrams" / f"{name}.svg").read_text(encoding="utf-8")
    svg = re.sub(r"^<\?xml[^>]*\?>\s*", "", svg)
    return svg.replace("my-svg", f"d-{name}")   # mermaid scopes its CSS by id; six inlined SVGs need six ids


def changes_rows() -> str:
    rows = []
    for d in sorted((ROOT / "openspec" / "changes").iterdir()):
        if not d.is_dir() or d.name == "archive" or not (d / "proposal.md").exists():
            continue
        num = d.name[1:5]
        links = [f'<a href="../openspec/changes/{esc(d.name)}/proposal.md">proposal</a>']
        for r in sorted((ROOT / "reports").glob(f"{num}-*.html")):
            links.append(f'<a href="{esc(r.name)}">{esc(r.stem[5:] or r.stem)}</a>')
        for n in sorted((ROOT / "notes" / "blog").glob(f"{num}-*.md")):
            links.append(f'<a href="../notes/blog/{esc(n.name)}">笔记</a>')
        rows.append(f'<tr><td class="n"><code>{esc(d.name)}</code></td><td>{esc(first_sentence(d / "proposal.md"))}</td>'
                    f'<td>{" · ".join(links)}</td></tr>')
    return "\n".join(rows)


def heldout_table(run: bool) -> str:
    if not run:
        return '<p class="src">本次构建未运行 <code>python3 -m eval.heldout</code>；留出世界数字见 <a href="../eval/EXPERIMENTS.md">eval/EXPERIMENTS.md</a>。</p>'
    try:
        p = subprocess.run([sys.executable, "-m", "eval.heldout"], cwd=ROOT, capture_output=True, text=True, timeout=300,
                           env={**__import__("os").environ, "FINOPS_LLM_MODE": "replay"})
        lines = [l for l in p.stdout.splitlines() if l.startswith("|")]
        # keep the summary table only (header + separator + rows), stop at the first non-table line
        if p.returncode != 0 or len(lines) < 3:
            raise RuntimeError(f"exit {p.returncode}")
    except Exception as e:  # noqa: BLE001 - the page must still build; say so on the page
        return f'<p class="src">运行 eval.heldout 失败（{esc(e)}），留出世界数字见 <a href="../eval/EXPERIMENTS.md">eval/EXPERIMENTS.md</a>。</p>'
    cells = [[c.strip() for c in l.strip("|").split("|")] for l in lines if not re.match(r"^\|[-| ]+\|$", l)]
    head, body = cells[0], cells[1:]
    t = "<tr>" + "".join(f"<th>{esc(c)}</th>" for c in head) + "</tr>"
    t += "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in body)
    return f'<div class="tw"><table>{t}</table></div>'


def metrics_html(run_heldout: bool) -> str:
    b = json.loads((ROOT / "eval" / "baseline.json").read_text())
    rows = []
    for k, v in b.items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                rows.append((f"{k}.{k2}", v2))
        else:
            rows.append((k, v))
    base = "".join(f"<tr><td><code>{esc(k)}</code></td><td>{esc(v)}</td></tr>" for k, v in rows)
    return (
        '<h3>CI 基线（<code>eval/baseline.json</code>）</h3>'
        '<p class="src">只有 recall 和 savings_recall 用来卡回归，其余只展示；基线只升不降。</p>'
        f'<div class="tw"><table><tr><th>指标</th><th>基线值</th></tr>{base}</table></div>'
        '<h3>样本内 vs 留出世界（<code>python3 -m eval.heldout</code>，LLM 走 replay 录像）</h3>'
        '<p class="src">样本内是 judge prompt 调试时用的账号，数字是上限；留出世界用同一个 agent 同一份 prompt，换成账号的下两个月。</p>'
        + heldout_table(run_heldout)
    )


def build(run_heldout: bool = True) -> str:
    toc = "".join(f'<a href="#{i}">{t}</a>' for i, t in [("about", "是什么"), ("path", "10 分钟读法"), ("diagrams", "六张图"),
                                                        ("changes", "改动一览"), ("evidence", "证据页"), ("metrics", "当前指标")])
    path = "".join(f'<li><span class="t">{esc(t)}</span><a href="{esc(h)}">{esc(n)}</a>：{esc(w)}</li>' for t, h, n, w in READ_PATH)
    figs = "".join(
        f'<h3>{esc(title)}</h3><figure><div class="diagram">{inline_svg(name)}</div>'
        f'<figcaption>{esc(cap)} 源文件：<a href="../docs/diagrams/{name}.mmd">docs/diagrams/{name}.mmd</a>'
        f'（<a href="../docs/diagrams/{name}.svg">svg</a>）</figcaption></figure>'
        for name, title, cap in DIAGRAMS)
    ev = "".join(
        f'<tr><td><a href="{"" if h.startswith("reports/") else "../"}{esc(h[8:] if h.startswith("reports/") else h)}">{esc(t)}</a></td>'
        f'<td>{esc(d)}</td><td><code>{esc(h)}</code></td></tr>' for h, t, d in EVIDENCE)
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>finops-agent 导读</title><style>{CSS}</style></head><body><main>
<h1>finops-agent 导读</h1>
<p class="lead">给面试官、评审和维护者自己的一页入口：项目是什么、怎么在 10 分钟里读完、该看的图和证据都在哪。本页由 <code>tools/build_index.py</code> 生成，不手改。</p>
<nav class="toc">{toc}</nav>

<h2 id="about">这个项目是什么</h2>
<p>一个带证据找云上浪费的 AWS FinOps agent，同时是一份用 spec、评估和护栏构建 LLM agent 的完整样例。只读，不需要真实 AWS 账号：合成账号和两个测试服务器就在仓库里。</p>
<div class="two">
<div class="card"><h3>第一部分 · FinOps</h3><p>领域模型（单价 × 用量 × 时长，挂在资源、服务、团队上）和成本优化方法 M0 到 M6：先删、再降、最后买承诺；潮汐不是浪费；节省不超过花费。产物是带证据和口径的发现、SLO、腐烂检测和节省核实。</p>
<p class="src"><a href="../docs/METHOD.md">docs/METHOD.md</a> · <a href="../docs/FINOPS_SLO.md">docs/FINOPS_SLO.md</a></p></div>
<div class="card"><h3>第二部分 · agent 工程</h3><p>怎么让一个 agent 可控、可度量、可改进：数字由代码算，LLM 只判断且被校验；元数据按不可信输入处理；三层只读；eval 基线只升不降；每个改动是一份 spec、按阶段的 commit 和带证据的验收。FinOps 是载体，这一部分才是重点。</p>
<p class="src"><a href="../README.md">README</a> · <a href="../CONTRIBUTING.md">CONTRIBUTING.md</a></p></div>
</div>

<h2 id="path">10 分钟读法</h2>
<ol class="path">{path}</ol>

<h2 id="diagrams">六张图</h2>
<p class="lead">每张图都有 mermaid 源文件和渲染好的 SVG，框图只画仓库里已有的东西。标识符保持英文，说明用中文。</p>
{figs}

<h2 id="changes">改动一览</h2>
<p class="lead">每个改动是一个 OpenSpec change。动机取自 proposal 的 Why 第一句；报告和笔记按编号匹配。</p>
<div class="tw"><table><tr><th>Change</th><th>为什么做</th><th>链接</th></tr>
{changes_rows()}
</table></div>

<h2 id="evidence">关键证据页</h2>
<div class="tw"><table><tr><th>页面</th><th>看什么</th><th>路径</th></tr>{ev}</table></div>

<h2 id="metrics">当前指标</h2>
{metrics_html(run_heldout)}
<p class="src">重新生成：<code>python3 tools/build_index.py</code>。图的重新渲染见 <a href="../docs/diagrams/README.md">docs/diagrams/README.md</a>。</p>
</main></body></html>
"""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-heldout", action="store_true")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    Path(a.out).write_text(build(not a.no_heldout), encoding="utf-8")
    print(a.out)


if __name__ == "__main__":
    main()
