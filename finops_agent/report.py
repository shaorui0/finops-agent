"""Render one run as a self-contained HTML report, organised by method step."""
from __future__ import annotations

from collections import Counter
from html import escape

from finops_agent import slo
from finops_agent.fivepart import LABELS

STEPS = [
    ("M0", "以终为始", "成本目标，以及衡量它们的 SLI"),
    ("M1_visibility_attribution", "可见性与归因", "每一块钱能否落到服务、owner 和环境上？"),
    ("M2_ranking", "二八排序", "钱花在哪，哪些比预期大"),
    ("M3_delete", "清理", "没人用的，或在做无用功的"),
    ("M4_downsize_schedule", "降配与调度", "长期过配与可调度的空闲时段"),
    ("M5_commitment", "承诺折扣", "Savings Plan / RI，放在清理和降配之后"),
    ("M6_architecture", "架构级", "改用量或时长，而不是单价"),
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
.fp{border-left:3px solid var(--line);padding:2px 0 2px 10px;margin:8px 0}.fp h4{font-size:13px;margin:0 0 2px;color:var(--accent)}.fp p{margin:2px 0}.fp pre{margin:4px 0;white-space:pre-wrap;word-break:break-all;font-size:12px}
.badge{font-size:12px;border-radius:4px;padding:1px 6px;border:1px solid var(--line);font-weight:600}.rev-none,.rev-low{color:var(--ok)}.rev-medium{color:var(--warn)}.rev-high{color:var(--bad)}
details summary{cursor:pointer;color:var(--muted);font-size:13px}.covered{color:var(--ok)}.partial{color:var(--warn)}.missing{color:var(--bad)}code{font-size:12px;word-break:break-all}.wrap{overflow-x:auto}
"""


REV_ZH = {"none": "无", "low": "低", "medium": "中", "high": "高"}


def _plan_html(plan) -> str:
    if not plan:
        return ""
    h = [f"<div><span class='badge rev-{plan['reversal_cost']}'>撤回成本：{REV_ZH.get(plan['reversal_cost'], plan['reversal_cost'])}</span> "
         f"<span class=tag>{escape(plan['plan_id'])}</span> <span class=tag>{escape(plan['mode'])}</span> "
         f"<span class=muted>{escape(plan['reversal_reason'])}</span></div>"]
    if plan["steps"]:
        h.append("<pre>" + escape("\n".join(plan["steps"])) + "</pre>")
    if plan["rollback"]:
        h.append("<div><b>回滚：</b></div><ul>" + "".join(f"<li><code>{escape(r)}</code></li>" for r in plan["rollback"]) + "</ul>")
    if plan.get("advice"):
        h.append(f"<div>{escape(plan['advice'])}</div>")
    h.append(f"<div class=muted><b>审批：</b>需人工审批；通知 {escape(plan['owner'])}。本次运行没有执行任何命令。</div>")
    return "".join(h)


def _fivepart_html(fp: dict, plan) -> str:
    """The five labelled parts of one finding card: 现状 / 期望 / 差异 / 处置 / 预防."""
    def part(key, body):
        return f"<section class='fp fp-{key}'><h4>{LABELS[key]}</h4>{body}</section>"
    lines = "".join(f"<li>{escape(x)}</li>" for x in fp["runbook"])
    prev = "".join(f"<p>{escape(x)}</p>" for x in fp["prevention"].split("\n"))
    return (part("status", f"<p>{escape(fp['status'])}</p>") + part("spec", f"<p>{escape(fp['spec'])}</p>") +
            part("diff", f"<p>{escape(fp['diff'])}</p>") +
            part("runbook", _plan_html(plan) + f"<ul>{lines}</ul>") + part("prevention", prev))


def _plans_overview(run: dict) -> str:
    pd = run["plans"]
    h = ["<h2>处置计划 <span class=muted>· dry-run，本次运行没有执行任何命令</span></h2>",
         f"<p>{len(pd['plans'])} 个计划，顺序：{escape(pd['order'])}。每个计划都带撤回成本和回滚；命令只是文本，由人审批后自己执行。"
         + (f" 没有处理器的 finding：{len(pd['skipped'])} 个。" if pd["skipped"] else "") + "</p>",
         "<div class=wrap><table><tr><th>计划</th><th>类型</th><th class=num>节省/月</th><th>撤回成本</th><th>模式</th><th>owner</th></tr>"]
    for p in pd["plans"]:
        h.append(f"<tr><td><b>{escape(p['plan_id'])}</b></td><td>{escape(p['type'])}</td><td class=num>{_usd(p['monthly_savings_usd'])}</td>"
                 f"<td><span class='badge rev-{p['reversal_cost']}'>{REV_ZH.get(p['reversal_cost'], p['reversal_cost'])}</span></td>"
                 f"<td>{escape(p['mode'])}</td><td>{escape(p['owner'])}</td></tr>")
    h.append("</table></div>")
    return "".join(h)


def _usd(v):
    return f"${v:,.2f}"


VERDICT_ZH = {"waste": "浪费", "not_waste": "不是浪费", "insufficient_evidence": "证据不足", None: "未判断"}


def _judgment_note(j):
    if not j:
        return ""
    if not j["accepted"]:
        return f"<div class=card><b class=missing>判断被拒绝</b>：{escape(str(j['reject_reason']))}</div>"
    fnd = f"，成为发现 {escape(j['finding'])}" if j["finding"] else "，没有产生发现"
    return (f"<div class=card><b>判断：{VERDICT_ZH.get(j['verdict'], j['verdict'])}</b>{fnd}"
            f"<div>{escape(j['title'] or '')}</div><div class=muted>{escape(j['reasoning'] or '')}</div></div>")


def _llm_cost(run: dict) -> str:
    calls = [c for c in run["trace"] if c["source"] == "llm"]
    h = ["<h2>Agent 成本 <span class=muted>· 判断层的每一次 LLM 调用</span></h2>"]
    if not calls:
        return h[0] + "<p class=muted>本次运行没有调用 LLM（判断层关闭）。</p>"
    tin, tout = sum(c["tokens_in"] for c in calls), sum(c["tokens_out"] for c in calls)
    cost, lat = sum(c["cost_usd"] for c in calls), [c["latency_ms"] for c in calls]
    rejected = sum(1 for c in calls if not c["accepted"])
    h.append("<div class=kpis>"
             f"<div class=kpi><span class=muted>调用次数</span><b>{len(calls)}</b></div>"
             f"<div class=kpi><span class=muted>输入 / 输出 tokens</span><b>{tin:,} / {tout:,}</b></div>"
             f"<div class=kpi><span class=muted>花费（录制值）</span><b>{_usd(cost)}</b></div>"
             f"<div class=kpi><span class=muted>延迟 平均 / 最大</span><b>{sum(lat) / len(lat) / 1000:.1f}s / {max(lat) / 1000:.1f}s</b></div>"
             f"<div class=kpi><span class=muted>被拒绝的判断</span><b class={'covered' if not rejected else 'missing'}>{rejected}</b></div>"
             "</div>")
    h.append(f"<p class=muted>模式 {escape(calls[0]['mode'])}；replay 模式下 tokens、花费、延迟都是录制时的真实值。每条线索一次独立调用，互相看不到对方的证据。</p>")
    h.append("<div class=wrap><table><tr><th>线索</th><th>模型</th><th class=num>输入</th><th class=num>输出</th><th class=num>延迟</th><th class=num>花费</th><th>结果</th></tr>")
    for c in calls:
        res = escape(str(c["verdict"])) if c["accepted"] else f"<span class=missing>拒绝：{escape(str(c['reject_reason']))}</span>"
        h.append(f"<tr><td>{escape(c['params']['lead'])} <span class=muted>{escape(c['params']['kind'])}</span></td><td>{escape(c['params']['model'])}</td>"
                 f"<td class=num>{c['tokens_in']:,}</td><td class=num>{c['tokens_out']:,}</td><td class=num>{c['latency_ms'] / 1000:.1f}s</td>"
                 f"<td class=num>{_usd(c['cost_usd'])}</td><td>{res}</td></tr>")
    h.append("</table></div>")
    return "".join(h)


def render(run: dict) -> str:
    f = run["findings"]
    total = run["ranking"]["total"]
    by_basis = Counter()
    for x in f:
        by_basis[x["basis"]] += x["monthly_savings_usd"]
    h = [f"<!doctype html><html lang=zh><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
         f"<title>FinOps 运行 {escape(run['run_id'])}</title><style>{CSS}</style></head><body><main>"]
    h.append(f"<h1>FinOps 运行 <code>{escape(run['run_id'])}</code></h1>"
             f"<div class=muted>账号 {escape(run['account'])} · 周期 {run['period']['Start']} → {run['period']['End']} · "
             f"{sum(1 for c in run['trace'] if c['source'] != 'llm')} 次只读 API 调用 · {sum(1 for c in run['trace'] if c['source'] == 'llm')} 次 LLM 调用</div>")
    inv = run["invariants"]
    fps = {x["finding_id"]: x for x in run.get("fivepart", [])}
    plans = {p["finding_id"]: p for p in run.get("plans", {}).get("plans", [])}
    h.append("<div class=kpis>"
             f"<div class=kpi><span class=muted>花费（amortized）</span><b>{_usd(total)}</b></div>"
             f"<div class=kpi><span class=muted>发现</span><b>{len(f)}</b></div>"
             f"<div class=kpi><span class=muted>节省（账单口径）</span><b>{_usd(sum(v for k, v in by_basis.items() if k.startswith('billed')))}</b></div>"
             f"<div class=kpi><span class=muted>节省（牌价口径）</span><b>{_usd(by_basis.get('list_price', 0))}</b></div>"
             f"<div class=kpi><span class=muted>待判断的线索</span><b>{len(run['leads'])}</b></div>"
             f"<div class=kpi><span class=muted>不变量</span><b class={'covered' if not inv else 'missing'}>{'通过' if not inv else f'{len(inv)} 条违反'}</b></div>"
             "</div>")
    if run.get("slo"):
        so = run["slo"]
        d = so["diff"]
        h.append("<h2>FinOps SLO <span class=muted>· 成本健康在保持，还是在腐烂？</span></h2>")
        h.append(f"<p>与上一次运行相比（此前共 {so['previous_runs']} 次运行）："
                 f"新增 <b>{len(d['new'])}</b> · 持续 <b>{len(d['persisting'])}</b> · 已解决 <b>{len(d['resolved'])}</b> · "
                 f"复发 <b class={'missing' if d['regressed'] else 'covered'}>{len(d['regressed'])}</b></p>")
        h.append("<div class=wrap><table><tr><th>SLI</th><th class=num>值</th><th>目标</th><th>状态</th><th>节奏</th><th>证据</th></tr>")
        for r in so["rows"]:
            v = slo.fmt(r["value"], r["unit"])
            t = f"{r['op']} {slo.fmt(r['target'], r['unit'])}"
            cls = {"ok": "covered", "violated": "missing"}.get(r["status"], "partial")
            extra = f" · 已用预算 {r['budget_used']:.0%}（预算 {_usd(r['budget_usd'])}）" if r.get("budget_usd") else ""
            h.append(f"<tr><td><b>{escape(r['id'])}</b><div class=muted>{escape(r['what'])}</div></td><td class=num>{v}</td><td>{escape(t)}</td>"
                     f"<td class={cls}>{r['status']}</td><td>{r['cadence']}</td><td>{escape(r['evidence'])}{extra}</td></tr>")
        h.append("</table></div>")
    if run.get("plans"):
        h.append(_plans_overview(run))
    if inv:
        h.append("<div class=card><h3 class=missing>违反不变量</h3><ul>" + "".join(f"<li>{escape(v)}</li>" for v in inv) + "</ul></div>")

    for key, zh, en in STEPS:
        h.append(f"<h2>{key.split('_')[0]} {zh} <span class=muted>· {en}</span></h2>")
        if key == "M0":
            gaps = run["visibility"]["gaps"]
            c = Counter(g["status"] for g in gaps)
            h.append(f"<p>成本目标需要 {len(gaps)} 个 SLI："
                     f"<span class=covered>{c['covered']} 个已覆盖</span>，<span class=partial>{c['partial']} 个部分覆盖</span>，"
                     f"<span class=missing>{c['missing']} 个缺失</span>。详见下方可见性链。</p>")
            continue
        if key == "M1_visibility_attribution":
            a = run["attribution"]
            h.append(f"<p>没有 <code>owner</code> tag 的花费：<b>{_usd(a['untagged_usd'])}</b> / {_usd(a['total_usd'])} "
                     f"（{a['untagged_share']:.0%}）。没有 owner 的实例：{'、'.join(a['instances_without_owner']) or '无'}。</p>")
        if key == "M2_ranking":
            r = run["ranking"]
            h.append("<div class=wrap><table><tr><th>服务</th><th class=num>Amortized</th><th class=num>占比</th></tr>" +
                     "".join(f"<tr><td>{escape(s)}</td><td class=num>{_usd(v)}</td><td class=num>{v / total:.0%}</td></tr>" for s, v in r["by_service"]) +
                     "</table></div>")
            for s in r["surprises"]:
                h.append(f"<div class=card><b>意外项：</b>{escape(s)}</div>")
        step_f = [x for x in f if x["method_step"] == key]
        step_l = [x for x in run["leads"] if x["method_step"] == key]
        for x in step_f:
            fp = fps.get(x["id"])
            plan = plans.get(x["id"])
            h.append(f"<div class='card finding' id='{escape(x['id'])}'>"
                     f"<h3>{escape(x['id'])} · {escape(x['title'])}</h3>"
                     f"<div class=muted>{escape(x['type'])} · 节省 <b>{_usd(x['monthly_savings_usd'])}</b> "
                     f"<span class=tag>{escape(x['basis'])}</span>"
                     + (f" · 资源花费 {_usd(x['resource_spend_usd'])}" if x.get('resource_spend_usd') is not None else "")
                     + f" · owner <b>{escape(x.get('owner', '未知'))}</b></div>"
                     f"<div class=muted>资源：<code>{escape('、'.join(x['resources']))}</code></div>"
                     + (_fivepart_html(fp, plan) if fp else "") +
                     "<details><summary>证据与推理链</summary><div class=chain>" + "".join(f"<span>{escape(hp)}</span>" for hp in x["hops"]) + "</div>"
                     "<div class=wrap><table><tr><th>来源</th><th>证据</th><th>出处</th></tr>" +
                     "".join(f"<tr><td>{escape(e['source'])}</td><td>{escape(e['what'])}</td><td><code>{escape(e['ref'])}</code></td></tr>" for e in x["evidence"]) +
                     "</table></div></details></div>")
        judged = {j["lead"]: j for j in run.get("judgments", [])}
        for l in step_l:
            h.append(f"<div class=card><h3>{escape(l['id'])} · 线索：{escape(l['signal'])}</h3>"
                     f"<div class=muted>需要跨源判断，才能成为一条发现。</div><ul>" +
                     "".join(f"<li>{escape(q)}</li>" for q in l["questions"]) + "</ul>" +
                     "".join(f"<div class=muted><code>{escape(e['ref'])}</code> {escape(e['what'])}</div>" for e in l["evidence"]) +
                     _judgment_note(judged.get(l["id"])) + "</div>")
        if not step_f and not step_l and key not in ("M1_visibility_attribution", "M2_ranking"):
            h.append("<p class=muted>确定性检测器在这一步没有发现。</p>")

    h.append("<h2>可见性链 <span class=muted>· ① 需求 → ② 计划 → ③ 搜索 → ④ 缺口</span></h2><div class=wrap><table>"
             "<tr><th>SLI</th><th>它保护的决策</th><th>信号</th><th>状态</th><th>覆盖</th><th>找到的指标</th></tr>")
    for g in run["visibility"]["gaps"]:
        for i, n in enumerate(g["needs"]):
            h.append("<tr>" + (f"<td rowspan={len(g['needs'])}><b>{escape(g['sli'])}</b></td><td rowspan={len(g['needs'])}>{escape(g['decision'])}</td>" if i == 0 else "") +
                     f"<td>{escape(n['signal'])}</td><td class={n['status']}>{n['status']}</td><td class=num>{n['covered']}/{n['expected']}</td>"
                     f"<td><code>{escape(', '.join(n['metrics']) or '—')}</code></td></tr>")
    h.append("</table></div>")

    h.append(_llm_cost(run))
    calls = Counter(f"{c['source']} {c['op']}" for c in run["trace"] if c["source"] != "llm")
    h.append("<h2>运行留痕 <span class=muted>· agent 发出的每一次调用</span></h2><div class=wrap><table><tr><th>调用</th><th class=num>次数</th></tr>" +
             "".join(f"<tr><td><code>{escape(k)}</code></td><td class=num>{v}</td></tr>" for k, v in sorted(calls.items())) + "</table></div>")
    h.append("</main></body></html>")
    return "".join(h)
