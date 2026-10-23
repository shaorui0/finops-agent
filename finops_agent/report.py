"""Render one run as a self-contained HTML report, organised by method step."""
from __future__ import annotations

from collections import Counter
from html import escape

STEPS = [
    ("M0", "以终为始", "Cost goals and the SLIs that measure them"),
    ("M1_visibility_attribution", "可见性与归因", "Can every dollar be traced to a service, owner and environment?"),
    ("M2_ranking", "二八排序", "Where the money goes, and what is larger than expected"),
    ("M3_delete", "清理", "Things nobody uses, or that do useless work"),
    ("M4_downsize_schedule", "降配与调度", "Long-term over-provisioning and idle schedules"),
    ("M5_commitment", "承诺折扣", "Savings Plans / RIs, after delete and downsize"),
    ("M6_architecture", "架构级", "Change usage or duration, not unit price"),
]

CSS = """
:root{--bg:#fbfaf7;--fg:#1d2330;--muted:#5d6675;--line:#e3e0d8;--card:#fff;--accent:#1f4e79;--warn:#a3561a;--ok:#2f6b3a;--bad:#9b2c2c}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#14171c;--fg:#e6e8eb;--muted:#9aa3ae;--line:#2a2f37;--card:#1b1f26;--accent:#7fb0e0;--warn:#e0a060;--ok:#7cc48a;--bad:#e08080}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif}
main{max-width:980px;margin:0 auto;padding:28px 16px 64px}h1{font-size:24px;margin:0 0 4px}h2{font-size:18px;margin:36px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:15px;margin:0 0 6px}.muted{color:var(--muted)}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:18px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}.kpi b{display:block;font-size:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px;margin:10px 0}
.chain{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}.chain span{border:1px solid var(--line);border-radius:999px;padding:2px 10px;font-size:13px}
.chain span+span:before{content:"→ ";color:var(--muted)}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600}.num{text-align:right;font-variant-numeric:tabular-nums}.tag{font-size:12px;border-radius:4px;padding:1px 6px;border:1px solid var(--line)}
.covered{color:var(--ok)}.partial{color:var(--warn)}.missing{color:var(--bad)}code{font-size:12px;word-break:break-all}.wrap{overflow-x:auto}
"""


def _usd(v):
    return f"${v:,.2f}"


def render(run: dict) -> str:
    f = run["findings"]
    total = run["ranking"]["total"]
    by_basis = Counter()
    for x in f:
        by_basis[x["basis"]] += x["monthly_savings_usd"]
    h = [f"<!doctype html><html lang=zh><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
         f"<title>FinOps run {escape(run['run_id'])}</title><style>{CSS}</style></head><body><main>"]
    h.append(f"<h1>FinOps run <code>{escape(run['run_id'])}</code></h1>"
             f"<div class=muted>Account {escape(run['account'])} · period {run['period']['Start']} → {run['period']['End']} · "
             f"{len(run['trace'])} read-only API calls</div>")
    inv = run["invariants"]
    h.append("<div class=kpis>"
             f"<div class=kpi><span class=muted>Spend (amortized)</span><b>{_usd(total)}</b></div>"
             f"<div class=kpi><span class=muted>Findings</span><b>{len(f)}</b></div>"
             f"<div class=kpi><span class=muted>Savings, billed basis</span><b>{_usd(sum(v for k, v in by_basis.items() if k.startswith('billed')))}</b></div>"
             f"<div class=kpi><span class=muted>Savings, list-price basis</span><b>{_usd(by_basis.get('list_price', 0))}</b></div>"
             f"<div class=kpi><span class=muted>Leads for judgment</span><b>{len(run['leads'])}</b></div>"
             f"<div class=kpi><span class=muted>Invariants</span><b class={'covered' if not inv else 'missing'}>{'pass' if not inv else f'{len(inv)} violated'}</b></div>"
             "</div>")
    if run.get("slo"):
        so = run["slo"]
        d = so["diff"]
        h.append("<h2>FinOps SLO <span class=muted>· is cost health holding, or rotting?</span></h2>")
        h.append(f"<p>Since the previous run ({so['previous_runs']} earlier runs): "
                 f"<b>{len(d['new'])}</b> new · <b>{len(d['persisting'])}</b> persisting · <b>{len(d['resolved'])}</b> resolved · "
                 f"<b class={'missing' if d['regressed'] else 'covered'}>{len(d['regressed'])}</b> regressed</p>")
        h.append("<div class=wrap><table><tr><th>SLI</th><th class=num>Value</th><th>Target</th><th>Status</th><th>Cadence</th><th>Evidence</th></tr>")
        for r in so["rows"]:
            v = "—" if r["value"] is None else (f"{r['value']:.1%}" if r["target"] <= 1 else f"{r['value']:g}")
            t = f"{r['op']} " + (f"{r['target']:.0%}" if r["target"] <= 1 else f"{r['target']:g}")
            cls = {"ok": "covered", "violated": "missing"}.get(r["status"], "partial")
            extra = f" · budget used {r['budget_used']:.0%} of {_usd(r['budget_usd'])}" if r.get("budget_usd") else ""
            h.append(f"<tr><td><b>{escape(r['id'])}</b><div class=muted>{escape(r['what'])}</div></td><td class=num>{v}</td><td>{escape(t)}</td>"
                     f"<td class={cls}>{r['status']}</td><td>{r['cadence']}</td><td>{escape(r['evidence'])}{extra}</td></tr>")
        h.append("</table></div>")
    if inv:
        h.append("<div class=card><h3 class=missing>Invariant violations</h3><ul>" + "".join(f"<li>{escape(v)}</li>" for v in inv) + "</ul></div>")

    for key, zh, en in STEPS:
        h.append(f"<h2>{key.split('_')[0]} {zh} <span class=muted>· {en}</span></h2>")
        if key == "M0":
            gaps = run["visibility"]["gaps"]
            c = Counter(g["status"] for g in gaps)
            h.append(f"<p>{len(gaps)} SLIs required by the cost goals: "
                     f"<span class=covered>{c['covered']} covered</span>, <span class=partial>{c['partial']} partial</span>, "
                     f"<span class=missing>{c['missing']} missing</span>. Details in the visibility chain below.</p>")
            continue
        if key == "M1_visibility_attribution":
            a = run["attribution"]
            h.append(f"<p>Untagged spend (no <code>owner</code>): <b>{_usd(a['untagged_usd'])}</b> of {_usd(a['total_usd'])} "
                     f"({a['untagged_share']:.0%}). Instances without owner: {', '.join(a['instances_without_owner']) or 'none'}.</p>")
        if key == "M2_ranking":
            r = run["ranking"]
            h.append("<div class=wrap><table><tr><th>Service</th><th class=num>Amortized</th><th class=num>Share</th></tr>" +
                     "".join(f"<tr><td>{escape(s)}</td><td class=num>{_usd(v)}</td><td class=num>{v / total:.0%}</td></tr>" for s, v in r["by_service"]) +
                     "</table></div>")
            for s in r["surprises"]:
                h.append(f"<div class=card><b>Surprise:</b> {escape(s)}</div>")
        step_f = [x for x in f if x["method_step"] == key]
        step_l = [x for x in run["leads"] if x["method_step"] == key]
        for x in step_f:
            h.append("<div class=card>"
                     f"<h3>{escape(x['id'])} · {escape(x['title'])}</h3>"
                     f"<div class=muted>{escape(x['type'])} · savings <b>{_usd(x['monthly_savings_usd'])}</b> "
                     f"<span class=tag>{escape(x['basis'])}</span>"
                     + (f" · resource spend {_usd(x['resource_spend_usd'])}" if x.get('resource_spend_usd') is not None else "") + "</div>"
                     "<div class=chain>" + "".join(f"<span>{escape(hp)}</span>" for hp in x["hops"]) + "</div>"
                     "<div class=wrap><table><tr><th>Source</th><th>Evidence</th><th>From</th></tr>" +
                     "".join(f"<tr><td>{escape(e['source'])}</td><td>{escape(e['what'])}</td><td><code>{escape(e['ref'])}</code></td></tr>" for e in x["evidence"]) +
                     "</table></div></div>")
        for l in step_l:
            h.append(f"<div class=card><h3>{escape(l['id'])} · lead: {escape(l['signal'])}</h3>"
                     f"<div class=muted>Needs cross-source judgment before it becomes a finding.</div><ul>" +
                     "".join(f"<li>{escape(q)}</li>" for q in l["questions"]) + "</ul>" +
                     "".join(f"<div class=muted><code>{escape(e['ref'])}</code> {escape(e['what'])}</div>" for e in l["evidence"]) + "</div>")
        if not step_f and not step_l and key not in ("M1_visibility_attribution", "M2_ranking"):
            h.append("<p class=muted>Nothing found at this step by the deterministic detectors.</p>")

    h.append("<h2>Visibility chain <span class=muted>· ① requirements → ② plan → ③ search → ④ gaps</span></h2><div class=wrap><table>"
             "<tr><th>SLI</th><th>Decision it protects</th><th>Signal</th><th>Status</th><th>Coverage</th><th>Metrics found</th></tr>")
    for g in run["visibility"]["gaps"]:
        for i, n in enumerate(g["needs"]):
            h.append("<tr>" + (f"<td rowspan={len(g['needs'])}><b>{escape(g['sli'])}</b></td><td rowspan={len(g['needs'])}>{escape(g['decision'])}</td>" if i == 0 else "") +
                     f"<td>{escape(n['signal'])}</td><td class={n['status']}>{n['status']}</td><td class=num>{n['covered']}/{n['expected']}</td>"
                     f"<td><code>{escape(', '.join(n['metrics']) or '—')}</code></td></tr>")
    h.append("</table></div>")

    calls = Counter(f"{c['source']} {c['op']}" for c in run["trace"])
    h.append("<h2>Run trace <span class=muted>· every call the agent made</span></h2><div class=wrap><table><tr><th>Call</th><th class=num>Count</th></tr>" +
             "".join(f"<tr><td><code>{escape(k)}</code></td><td class=num>{v}</td></tr>" for k, v in sorted(calls.items())) + "</table></div>")
    h.append("</main></body></html>")
    return "".join(h)
