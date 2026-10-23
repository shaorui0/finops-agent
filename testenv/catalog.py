"""Render the synthetic account's ground truth as one readable HTML page.

    python3 -m testenv.catalog --out reports/testenv-catalog.html

Every case in `world.yaml` (`ground_truth`) and every expected change in the two scenario
overlays carries five parts: status, spec, diff, runbook, prevention. Their text may contain
placeholders such as `{cost:vol-...}` or `{sav:GT06}`; `render_text` resolves them against
`testenv.world.load()`, so no number shown on the page is typed into prose.

Placeholder grammar: `{name}` or `{name:arg}`; an arg may end in `@base`, `@next` or `@self`
to pick the world (self = the world the text belongs to; for ground truth that is the base).
`alert:Name` in a prevention text marks an alert rule defined in config/alerts/finops.rules.yml.
"""
from __future__ import annotations

import argparse
import html
import random
import re
import statistics
from datetime import date, timedelta
from pathlib import Path

import yaml

from testenv import world as W

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = [("next_month", ROOT / "testenv/scenarios/next_month.yaml", 2),
             ("month_after", ROOT / "testenv/scenarios/month_after.yaml", 3)]
RULES_FILE = ROOT / "config/alerts/finops.rules.yml"
FIELDS = ("status", "spec", "diff", "runbook", "prevention")
PLACEHOLDER = re.compile(r"\{([a-z_0-9]+)(?::([^{}\"=]+?))?\}")
ALERT_REF = re.compile(r"alert:([A-Za-z0-9_]+)")


# ---- data loading ------------------------------------------------------------
def ground_truth() -> dict:
    return W.load(W.WORLD_FILE).raw["ground_truth"]


def scenario_docs() -> list[dict]:
    out = []
    for name, path, periods in SCENARIOS:
        sc = yaml.safe_load(path.read_text())["scenario"]
        out.append({"name": name, "path": path, "periods": periods, "scenario": sc})
    return out


def alert_names() -> set[str]:
    rules = yaml.safe_load(RULES_FILE.read_text())
    return {r["alert"] for g in rules["groups"] for r in g["rules"] if "alert" in r}


def slo_targets() -> dict:
    cfg = yaml.safe_load((ROOT / "config/finops_slo.yaml").read_text())
    return {s["id"]: s for s in cfg["slos"]}


# ---- placeholder resolution ----------------------------------------------------
def money(x: float) -> str:
    return f"${x:,.0f}" if abs(x) >= 100 else f"${x:,.2f}"


def _num(x) -> str:
    if isinstance(x, float):
        return f"{x:g}" if abs(x) < 1 else f"{x:,.2f}".rstrip("0").rstrip(".")
    if isinstance(x, int):
        return f"{x:,}"
    s = str(x)
    return s[:10] if re.match(r"\d{4}-\d\d-\d\dT", s) else s


class Ctx:
    """The worlds a text may refer to. `self` is the world the text belongs to."""

    def __init__(self, self_path=None, next_path=None, periods: int = 1):
        self.paths = {"base": W.WORLD_FILE, "self": self_path or W.WORLD_FILE, "next": next_path or self_path or W.WORLD_FILE}
        self.periods = periods
        self.gt = ground_truth()

    def world(self, which: str) -> W.World:
        return W.load(self.paths[which])


def _period_lines(w: W.World, pred):
    s, e = w.period
    return [l for l in w.lines if s <= l.day < e and pred(l)]


def _sum(w, pred) -> float:
    return sum(l.unblended for l in _period_lines(w, pred))


def _is_box(l) -> bool:
    return l.usage_type.startswith("BoxUsage")


def _cpu_samples(w: W.World, inst: dict) -> list[float]:
    s, e = w.period
    t0 = W._ts(s.isoformat() + "T00:00:00Z")
    n = int((e - s).days * 24)
    rng = random.Random(7)
    vals = [W.cpu(w, inst, t0 + h * 3600, rng) for h in range(n)]
    return [v for v in vals if v is not None]


def _inst_or_asg(w: W.World, ident: str) -> dict:
    for i in w.instances:
        if i["id"] == ident or i.get("asg") == ident:
            return i
    raise KeyError(ident)


def _split(arg: str | None) -> tuple[str, str]:
    arg = arg or ""
    if "@" in arg:
        a, which = arg.rsplit("@", 1)
        return a, which
    return arg, "self"


def _vol(w: W.World, vid: str) -> dict:
    return next(v for v in w.all_volumes() if v["id"] == vid)


def _snapshots_for(w: W.World, arg: str) -> list[dict]:
    snaps = w.snapshots()
    if arg.startswith("gt:"):
        gid = arg[3:]
        ctx_gt = ground_truth()
        entry = next(x for x in ctx_gt["findings"] + ctx_gt["traps"] if x["id"] == gid)
        imgs = {r for r in entry["resources"] if r.startswith("ami-")}
        return [s for s in snaps if s["image"] in imgs]
    return [s for s in snaps if s["volume_id"] == arg]


def resolve(name: str, arg: str | None, ctx: Ctx) -> str:
    a, which = _split(arg)
    w = ctx.world(which)
    raw = w.raw
    if name == "cost":
        return money(_sum(w, lambda l: l.resource_id == a))
    if name == "box":
        return money(_sum(w, lambda l: l.resource_id == a and _is_box(l)))
    if name == "ut":
        return money(_sum(w, lambda l: l.usage_type == a))
    if name == "fleet":
        ids = {i["id"] for i in w.instances if i.get("asg") == a}
        return money(_sum(w, lambda l: l.resource_id in ids and _is_box(l)))
    if name == "svc_count":
        return str(sum(1 for i in w.instances if i["tags"].get("service") == a))
    if name == "count":
        return str(sum(1 for i in w.instances if i.get("asg") == a))
    if name == "cpu_avg":
        return f"{statistics.mean(_cpu_samples(w, _inst_or_asg(w, a))):.0f}%"
    if name == "cpu_max":
        return f"{max(_cpu_samples(w, _inst_or_asg(w, a))):.0f}%"
    if name == "p":
        cur = raw
        for part in a.split("."):
            cur = cur[part]
        return _num(cur)
    if name == "len":
        cur = raw
        for part in a.split("."):
            cur = cur[part]
        return str(len(cur))
    if name in ("inst", "vol", "eip"):
        ident, field = a.rsplit(".", 1)
        if name == "inst":
            obj = w.instance(ident)
        elif name == "vol":
            obj = _vol(w, ident)
        else:
            obj = next(x for x in raw["addresses"] if x["allocation_id"] == ident)
        return _num(obj[field])
    if name == "sp":
        return _num(raw["savings_plans"][0][a])
    if name in ("sp_pct", "sp_unused"):
        s, e = w.period
        days = [s + timedelta(days=k) for k in range((e - s).days)]
        u = [w.sp_utilization(d) for d in days]
        if name == "sp_pct":
            return f"{100 * sum(x['used'] for x in u) / sum(x['total'] for x in u):.0f}%"
        return money(sum(x["unused"] for x in u))
    if name == "sav":
        gt = next(f for f in ctx.gt["findings"] if f["id"] == a)["monthly_savings_usd"]
        return f"{money(gt['min'])} 至 {money(gt['max'])}" if gt["max"] else "$0"
    if name == "slo":
        s = slo_targets()[a]
        t = s["target"]
        op = {">=": "≥", "<=": "≤"}[s["op"]]
        return f"{op} {t * 100:.0f}%" if s["unit"] == "ratio" else f"{op} {t} 天"
    if name == "nat_base":
        u = raw["usage"]
        return money(u["nat_gb_baseline_month"] * w.prices["nat_gb"])
    if name == "nat_excess":
        u = raw["usage"]
        return money(_sum(w, lambda l: l.usage_type == "NatGateway-Bytes") - u["nat_gb_baseline_month"] * w.prices["nat_gb"])
    if name in ("dev_idle_pct", "dev_naive"):
        s, e = w.period
        hours = [(s + timedelta(days=d), h) for d in range((e - s).days) for h in range(24)]
        idle = sum(1 for d, h in hours if not (d.weekday() < 5 and h < 10)) / len(hours)
        if name == "dev_idle_pct":
            return f"{100 * idle:.0f}%"
        ids = {i["id"] for i in w.instances if i["tags"].get("service") == "web-dev"}
        return money(_sum(w, lambda l: l.resource_id in ids and _is_box(l)) * idle)
    if name == "etl_idle":
        return money(_sum(w, lambda l: l.resource_id == a and _is_box(l)) * 22 / 24)
    if name == "gp2cost":
        v = _vol(w, a)
        return money(w.prices["ebs_gb_month"]["gp2"] * v["size"])
    if name == "gp3cost":
        v = _vol(w, a)
        return money(w.prices["ebs_gb_month"]["gp3"] * v["size"])
    if name == "gp_delta":
        v = _vol(w, a)
        pr = w.prices["ebs_gb_month"]
        return money((pr["gp2"] - pr["gp3"]) * v["size"])
    if name == "snap_archive":
        v = _vol(w, a)
        return money(w.prices["snapshot_gb_month"] * v["size"])
    if name == "snapvol":
        ids = {s["id"] for s in _snapshots_for(w, a)}
        return money(_sum(w, lambda l: l.resource_id in ids))
    if name == "snapn":
        return str(len(_snapshots_for(w, a)))
    if name == "age":
        v = _vol(w, a)
        return str((w.period[1] - W._d(v["created"])).days)
    if name == "inc_date":
        return raw["usage"]["incident_start"][5:10]
    if name == "period":
        s, e = w.period
        return f"{s.isoformat()[:7]}"
    if name == "periods":
        return str(ctx.periods)
    raise KeyError(f"unknown placeholder {name}")


def render_text(text: str, ctx: Ctx) -> str:
    """Replace every placeholder in `text`; raises KeyError on an unknown one."""
    return PLACEHOLDER.sub(lambda m: resolve(m.group(1), m.group(2), ctx), text)


def unresolved(text: str) -> list[str]:
    return [m.group(0) for m in PLACEHOLDER.finditer(text)]


def five_parts(entry: dict, ctx: Ctx) -> dict:
    out = {}
    for f in FIELDS:
        v = entry[f]
        out[f] = [render_text(x, ctx) for x in v] if isinstance(v, list) else render_text(v, ctx)
    return out


# ---- HTML helpers --------------------------------------------------------------
BADGES = {"[不可逆]": ("irrev", "不可逆"), "[需人工审批]": ("appr", "需人工审批"), "[只读]": ("ro", "只读"), "[可回滚]": ("rb", "可回滚")}


def inline(text: str) -> str:
    """Escape, then mark up `code`, alert:Name and the safety badges."""
    s = html.escape(text, quote=False)
    s = ALERT_REF.sub(lambda m: f'<code class="alert">{m.group(1)}</code>', s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    for tag, (cls, label) in BADGES.items():
        s = s.replace(html.escape(tag, quote=False), f'<span class="badge {cls}">{label}</span>')
    return s


def paras(text: str) -> str:
    out = []
    for line in text.strip().splitlines():
        m = re.match(r"^(控制|告警|节奏)：(.*)$", line)
        if m:
            out.append(f'<p><b class="lab">{html.escape(m.group(1))}</b>{inline(m.group(2))}</p>')
        else:
            out.append(f"<p>{inline(line)}</p>")
    return "".join(out)


PHASE = {"验证": "v", "处置": "a", "确认": "c"}


def runbook_html(steps: list[str]) -> str:
    items = []
    for s in steps:
        m = re.match(r"^(验证|处置|确认)：(.*)$", s, re.S)
        if m:
            items.append(f'<li><span class="ph {PHASE[m.group(1)]}">{m.group(1)}</span>{inline(m.group(2))}</li>')
        else:
            items.append(f"<li>{inline(s)}</li>")
    return "<ol class=\"runbook\">" + "".join(items) + "</ol>"


def five_html(p: dict) -> str:
    return (
        '<div class="cols"><section class="part status"><h4>现状 status</h4>' + paras(p["status"]) + "</section>"
        '<section class="part spec"><h4>期望 spec</h4>' + paras(p["spec"]) + "</section></div>"
        '<section class="part diff"><h4>差异 diff</h4>' + paras(p["diff"]) + "</section>"
        '<section class="part rb"><h4>处置 runbook</h4>' + runbook_html(p["runbook"]) + "</section>"
        '<section class="part prev"><h4>预防 prevention</h4>' + paras(p["prevention"]) + "</section>"
    )


STEP_LABEL = {
    "M1_visibility_attribution": "M1 可见性与归因", "M3_delete": "M3 删除", "M4_downsize_schedule": "M4 降配与排程",
    "M5_commitment": "M5 承诺", "M6_architecture": "M6 架构",
}


def chip_list(items) -> str:
    return " ".join(f"<code>{html.escape(str(i))}</code>" for i in items)


def sav_cell(sv: dict, max_all: float) -> str:
    lo, hi = sv["min"], sv["max"]
    w_lo, w_hi = 100 * lo / max_all, 100 * hi / max_all
    label = f"{money(lo)} 至 {money(hi)}" if hi else "$0"
    bar = f'<span class="bar"><i style="left:0;width:{w_lo:.1f}%" class="lo"></i><i style="left:{w_lo:.1f}%;width:{max(w_hi - w_lo, 0.6):.1f}%" class="hi"></i></span>' if hi else '<span class="bar"></span>'
    return f'<td class="sav">{label}{bar}</td>'


# ---- diagrams ------------------------------------------------------------------
def architecture_svg(n_find: int, n_trap: int, n_gap: int, n_scen: int) -> str:
    def box(x, y, w, h, title, sub="", cls="n"):
        t = f'<text x="{x + w / 2}" y="{y + (h / 2 - 2 if sub else h / 2 + 5)}" text-anchor="middle" class="t">{html.escape(title)}</text>'
        s = f'<text x="{x + w / 2}" y="{y + h / 2 + 14}" text-anchor="middle" class="s">{html.escape(sub)}</text>' if sub else ""
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" class="{cls}"/>{t}{s}'

    def arrow(x1, y1, x2, y2):
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="ar" marker-end="url(#ah)"/>'

    parts = [
        box(10, 20, 130, 52, "world.yaml", "唯一数据源", "src"),
        box(180, 20, 130, 52, "world.py", "推导成本行与指标"),
        box(350, 4, 150, 40, "test-aws-server", ":4566  只读"),
        box(350, 52, 150, 40, "test-metrics-server", ":9090  PromQL 子集"),
        box(540, 20, 130, 52, "finops_agent", "巡检流水线"),
        box(700, 20, 130, 52, "findings.json", "agent 的答案"),
        box(10, 150, 220, 62, "ground_truth（五段式）", f"{n_find} 个发现  {n_trap} 个陷阱  {n_gap} 个可见性缺口", "gt"),
        box(270, 150, 150, 62, f"{n_scen} 个场景覆盖层", "next_month  month_after", "gt"),
        box(540, 150, 130, 52, "eval.score", "对答案打分"),
        box(700, 150, 130, 52, "catalog.py", "生成本页", "src"),
        arrow(140, 46, 180, 46), arrow(310, 36, 350, 26), arrow(310, 56, 350, 72),
        arrow(500, 24, 540, 40), arrow(500, 72, 540, 56), arrow(670, 46, 700, 46),
        arrow(765, 72, 605, 150), arrow(230, 181, 540, 178), arrow(75, 72, 75, 150), arrow(420, 181, 700, 181),
    ]
    return (
        '<svg viewBox="0 0 840 230" role="img" aria-label="测试环境架构图" class="diagram">'
        '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="ahp"/></marker></defs>'
        + "".join(parts) + "</svg>"
    )


def flow_html() -> str:
    steps = [("现状", "status", "系统现在什么样，带资源状态与数字"), ("期望", "spec", "它应该什么样，陷阱则说明现状为何就是规格"),
             ("差异", "diff", "两者的差距，尽量量化"), ("处置", "runbook", "验证、动作、确认，有序"), ("预防", "prevention", "什么控制让它不再发生")]
    return '<div class="flow">' + "".join(f'<div class="step s{i}"><b>{a}</b><code>{b}</code><span>{c}</span></div>' for i, (a, b, c) in enumerate(steps)) + "</div>"


# ---- page ------------------------------------------------------------------------
CSS = """
:root{--bg:#fbfbf9;--fg:#1b1d21;--mut:#5b616b;--line:#dcdfe4;--card:#fff;--acc:#2a5db0;--st:#f3f6fb;--sp:#f1f8f3;--df:#fff6e8;--df-b:#e3a84a;--pv:#f5f2fb;--rb:#fff;--bad:#b3261e;--ok:#1d7a46;--warn:#9a6a00;--code:#eef0f3;--bar:#c9d6ee;--bar2:#2a5db0}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#14161a;--fg:#e6e8eb;--mut:#9aa1ab;--line:#2d3138;--card:#1b1e23;--acc:#7fa8e8;--st:#1a2230;--sp:#17261d;--df:#2b2214;--df-b:#a87a2a;--pv:#231f30;--rb:#1b1e23;--bad:#f2867f;--ok:#6fcf97;--warn:#e0b04a;--code:#262a31;--bar:#2e3d5c;--bar2:#7fa8e8}}
:root[data-theme=dark]{--bg:#14161a;--fg:#e6e8eb;--mut:#9aa1ab;--line:#2d3138;--card:#1b1e23;--acc:#7fa8e8;--st:#1a2230;--sp:#17261d;--df:#2b2214;--df-b:#a87a2a;--pv:#231f30;--rb:#1b1e23;--bad:#f2867f;--ok:#6fcf97;--warn:#e0b04a;--code:#262a31;--bar:#2e3d5c;--bar2:#7fa8e8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC","Segoe UI",sans-serif}
main{max-width:1040px;margin:0 auto;padding:20px 16px 64px}h1{font-size:1.7rem;margin:.2em 0}h2{font-size:1.3rem;margin:2.2em 0 .6em;padding-bottom:.25em;border-bottom:1px solid var(--line)}h3{font-size:1.05rem;margin:0}h4{margin:0 0 .35em;font-size:.82rem;letter-spacing:.04em;color:var(--mut)}
p{margin:.3em 0}code{background:var(--code);padding:.05em .35em;border-radius:4px;font:.86em ui-monospace,Menlo,monospace;word-break:break-all}code.alert{color:var(--warn);font-weight:600}
.lead{color:var(--mut);max-width:70ch}.meta{color:var(--mut);font-size:.85rem}
.diagram{width:100%;height:auto;margin:.5em 0}.diagram rect{fill:var(--card);stroke:var(--line);stroke-width:1.2}.diagram rect.src{stroke:var(--acc);stroke-width:2}.diagram rect.gt{fill:var(--sp);stroke:var(--ok)}.diagram .t{fill:var(--fg);font:600 13px sans-serif}.diagram .s{fill:var(--mut);font:11px sans-serif}.diagram .ar{stroke:var(--mut);stroke-width:1.5}.diagram .ahp{fill:var(--mut)}
.flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:.6em 0}.step{border:1px solid var(--line);border-radius:8px;padding:8px 10px;background:var(--card);display:flex;flex-direction:column;gap:2px}.step b{font-size:1rem}.step span{font-size:.8rem;color:var(--mut)}.step.s0{background:var(--st)}.step.s1{background:var(--sp)}.step.s2{background:var(--df)}.step.s4{background:var(--pv)}
table{width:100%;border-collapse:collapse;font-size:.88rem}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--mut);font-weight:600;white-space:nowrap}.tw{overflow-x:auto}
td.sav{white-space:nowrap;min-width:150px}td code{word-break:normal;white-space:nowrap}.dg{overflow-x:auto}.dg .diagram{min-width:640px}.bar{display:block;position:relative;height:5px;background:var(--line);border-radius:3px;margin-top:3px}.bar i{position:absolute;top:0;height:5px;border-radius:3px}.bar .lo{background:var(--bar)}.bar .hi{background:var(--bar2)}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:14px 0}.card.trap{border-left:4px solid var(--warn)}.card.st-regressed{border-left:4px solid var(--bad)}.card.st-new{border-left:4px solid var(--acc)}.card.st-resolved{border-left:4px solid var(--ok)}
.hd{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:baseline;margin-bottom:6px}.id{font:700 1rem ui-monospace,Menlo,monospace;color:var(--acc)}.chip{font-size:.75rem;border:1px solid var(--line);border-radius:999px;padding:0 8px;color:var(--mut);white-space:nowrap}
.hops{margin:.3em 0 .6em;padding-left:1.3em;color:var(--mut);font-size:.85rem}.hops li{margin:0}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media (max-width:680px){.cols{grid-template-columns:1fr}}
.part{border-radius:8px;padding:9px 12px;margin:10px 0 0;border:1px solid var(--line)}.part.status{background:var(--st);margin-top:0}.part.spec{background:var(--sp);margin-top:0}.part.diff{background:var(--df);border-color:var(--df-b)}.part.rb{background:var(--rb)}.part.prev{background:var(--pv)}
.cols .part{margin:10px 0 0}.lab{color:var(--mut);margin-right:.5em}
ol.runbook{margin:.2em 0;padding-left:1.4em}ol.runbook li{margin:.35em 0}.ph{display:inline-block;font-size:.72rem;font-weight:700;border-radius:4px;padding:0 6px;margin-right:6px;color:#fff}.ph.v{background:#5b7fc0}.ph.a{background:#c27a1a}.ph.c{background:#2f8f5b}
.badge{font-size:.7rem;font-weight:700;border-radius:4px;padding:0 5px;margin:0 3px;border:1px solid}.badge.irrev{color:var(--bad);border-color:var(--bad)}.badge.appr{color:var(--warn);border-color:var(--warn)}.badge.ro{color:var(--ok);border-color:var(--ok)}.badge.rb{color:var(--acc);border-color:var(--acc)}
.res{margin-top:8px;font-size:.8rem;color:var(--mut)}
.tl td,.tl th{text-align:center}.tl td:first-child,.tl th:first-child{text-align:left}.pill{display:inline-block;font-size:.78rem;border-radius:999px;padding:0 9px;border:1px solid var(--line)}.pill.open,.pill.persisting{color:var(--warn);border-color:var(--warn)}.pill.resolved{color:var(--ok);border-color:var(--ok)}.pill.new{color:var(--acc);border-color:var(--acc)}.pill.regressed{color:var(--bad);border-color:var(--bad);font-weight:700}.pill.none{color:var(--mut)}
.story{border-left:3px solid var(--acc);padding:2px 12px;margin:.6em 0;color:var(--mut)}
footer{margin-top:3em;color:var(--mut);font-size:.8rem}
"""


def build() -> str:
    gt = ground_truth()
    base_ctx = Ctx()
    base = base_ctx.world("base")
    s, e = base.period
    total = _sum(base, lambda l: True)
    max_all = max(f["monthly_savings_usd"]["max"] for f in gt["findings"])
    findings, traps, gaps = gt["findings"], gt["traps"], gt["visibility_gaps"]
    scen = scenario_docs()

    h = []
    h.append(f"<h1>测试账号目录</h1><p class=\"lead\">合成账号 <code>testenv/world.yaml</code> 的全部标准答案：{len(findings)} 个发现、{len(traps)} 个陷阱、{len(scen)} 个腐化场景、{len(gaps)} 个可见性缺口。"
             f"每个 case 按 现状 → 期望 → 差异 → 处置 → 预防 五段呈现。页内所有金额与比例由成本模型计算（周期 {s} 至 {e}，当月总账单 {money(total)}），不是手写。</p>")
    h.append("<h2>怎么读</h2>" + flow_html())
    h.append("<h2>数据从哪来</h2><div class=\"dg\">" + architecture_svg(len(findings), len(traps), len(gaps), len(scen)) + "</div>")

    h.append("<h2>总览</h2><div class=\"tw\"><table><thead><tr><th>id</th><th>方法步骤</th><th>跳数</th><th>月节省区间</th><th>一句话</th></tr></thead><tbody>")
    for f in findings:
        h.append(f'<tr><td><a href="#{f["id"]}"><code>{f["id"]}</code></a></td><td>{STEP_LABEL.get(f["method_step"], f["method_step"])}</td><td>{len(f["hops"])}</td>'
                 f'{sav_cell(f["monthly_savings_usd"], max_all)}<td>{html.escape(f["title"])}</td></tr>')
    for t in traps:
        h.append(f'<tr><td><a href="#{t["id"]}"><code>{t["id"]}</code></a></td><td>陷阱</td><td>0</td><td class="sav">不得 <code>{t["must_not"]}</code></td><td>{html.escape(t["why"])}</td></tr>')
    h.append("</tbody></table></div>")

    h.append("<h2>发现</h2>")
    for f in findings:
        p = five_parts(f, base_ctx)
        sv = f["monthly_savings_usd"]
        label = f"{money(sv['min'])} 至 {money(sv['max'])} / 月" if sv["max"] else "节省 $0"
        h.append(f'<article class="card" id="{f["id"]}"><div class="hd"><span class="id">{f["id"]}</span><h3>{html.escape(f["title"])}</h3></div>'
                 f'<div class="hd"><span class="chip">{STEP_LABEL.get(f["method_step"], f["method_step"])}</span><span class="chip">{len(f["hops"])} 跳</span><span class="chip">{label}</span>'
                 f'<span class="chip">证据 {", ".join(f["evidence_sources"])}</span></div>'
                 "<ol class=\"hops\">" + "".join(f"<li>{inline(x)}</li>" for x in f["hops"]) + "</ol>"
                 + five_html(p) + f'<div class="res">资源 {chip_list(f["resources"])}</div></article>')

    h.append("<h2>陷阱</h2><p class=\"lead\">看起来像浪费，实际不该动。检测器必须靠逻辑绕开，不靠名单。</p>")
    for t in traps:
        p = five_parts(t, base_ctx)
        h.append(f'<article class="card trap" id="{t["id"]}"><div class="hd"><span class="id">{t["id"]}</span><h3>不得 {t["must_not"]}</h3></div>'
                 f'<p class="meta">{html.escape(t["why"])}</p>' + five_html(p) + f'<div class="res">资源 {chip_list(t["resources"])}</div></article>')

    h.append("<h2>腐化场景时间线</h2><p class=\"lead\">三个周期：base（2026-09）→ next_month（2026-10）→ month_after（2026-11）。只有「上次 open、这次消失」的 key 才算 resolved，之后再出现才算 regressed，所以两次运行演示不了回归。</p>")
    h.append(timeline_html(scen))
    for sd in scen:
        h.append(scenario_html(sd, base_ctx))

    h.append("<h2>可见性缺口</h2><p class=\"lead\">故意埋下的数据缺口：agent 应当报告缺什么，而不是编一个数。</p><div class=\"tw\"><table><thead><tr><th>SLI</th><th>缺的数据</th><th>原因</th></tr></thead><tbody>")
    for g in gaps:
        h.append(f'<tr><td><code>{g["sli"]}</code></td><td>{html.escape(g["missing"])}</td><td>{html.escape(g["why"])}</td></tr>')
    h.append("</tbody></table></div>")
    h.append("<footer>由 <code>python3 -m testenv.catalog</code> 从 world.yaml、场景覆盖层、config/alerts/finops.rules.yml 与 config/finops_slo.yaml 生成。不要手改本页。</footer>")

    return ("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>测试账号目录</title><style>" + CSS + "</style></head><body><main>" + "".join(h) + "</main></body></html>")


def _timeline_states(scen: list[dict]) -> list[tuple[str, list[str]]]:
    """Per key: [base, next_month, month_after] states."""
    nxt, aft = scen[0]["scenario"]["expect"], scen[1]["scenario"]["expect"]
    keys: list[str] = []
    for ex in (nxt, aft):
        for st in ("resolved", "new", "regressed", "persisting"):
            for k in ex.get(st, []):
                if k not in keys:
                    keys.append(k)
    rows = []
    for k in keys:
        in_next = next((st for st in ("resolved", "new", "regressed", "persisting") if k in nxt.get(st, [])), None)
        in_after = next((st for st in ("resolved", "new", "regressed", "persisting") if k in aft.get(st, [])), None)
        base_state = "—" if in_next == "new" else "open"
        n = in_next or "—"
        a = in_after or ("已关闭" if in_next == "resolved" else "—")
        rows.append((k, [base_state, n, a]))
    return rows


def _pill(state: str) -> str:
    cls = {"open": "open", "persisting": "persisting", "resolved": "resolved", "new": "new", "regressed": "regressed"}.get(state, "none")
    return f'<span class="pill {cls}">{state}</span>'


def timeline_html(scen: list[dict]) -> str:
    out = ['<div class="tw"><table class="tl"><thead><tr><th>finding key</th><th>base 09</th><th>next_month 10</th><th>month_after 11</th></tr></thead><tbody>']
    for k, st in _timeline_states(scen):
        out.append(f"<tr><td><code>{html.escape(k)}</code></td>" + "".join(f"<td>{_pill(x)}</td>" for x in st) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


STATE_ORDER = [("regressed", "回归 regressed"), ("new", "新增 new"), ("resolved", "已解决 resolved"), ("persisting", "持续 persisting")]


def scenario_ctx(sd: dict) -> Ctx:
    nxt = SCENARIOS[0][1]
    return Ctx(self_path=sd["path"], next_path=nxt, periods=sd["periods"])


def scenario_html(sd: dict, base_ctx: Ctx) -> str:
    sc = sd["scenario"]
    ctx = scenario_ctx(sd)
    w = ctx.world("self")
    s, e = w.period
    out = [f'<h3 style="margin-top:1.6em">{sd["name"]}（{s.isoformat()[:7]}）</h3>']
    story = sc.get("story")
    if story:
        out.append(f'<div class="story"><p><b>{inline(render_text(story["headline"], ctx))}</b></p><p>{inline(render_text(story["narrative"], ctx))}</p></div>')
    details = sc["expect"]["details"]
    for st, label in STATE_ORDER:
        for key in sc["expect"].get(st, []):
            d = details[key]
            p = five_parts(d, ctx)
            out.append(f'<article class="card st-{st}"><div class="hd"><span class="pill {st}">{label}</span><span class="id">{d["gt"]}</span><code>{html.escape(key)}</code></div>' + five_html(p) + "</article>")
    return "".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="output HTML file")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build())
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
