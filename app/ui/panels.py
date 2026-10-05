"""Results dashboard and 'How it works' panels (self-contained HTML, offline)."""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
RESULTS_JSON = ROOT / "docs" / "results.json"

BASE_CSS = """
:root{--bg:#070a12;--surface:#0d1424;--surface2:#111b30;--line:#1e2b45;--line2:#2a3a5c;--text:#e6eefc;--mute:#8ea0ba;
--user:#4ade80;--ver:#60a5fa;--unt:#fb923c;--block:#f87171;--laya:#a78bfa;--cyan:#7dd3fc;
--font:'Montserrat','Segoe UI',system-ui,sans-serif;--mono:Consolas,'Cascadia Mono',ui-monospace,monospace}
*{box-sizing:border-box}html,body{margin:0;background:transparent;color:var(--text);font-family:var(--font);font-size:15px;line-height:1.5;overflow-x:hidden}
h2{margin:0 0 10px;font-size:13px;letter-spacing:1.4px;text-transform:uppercase;color:var(--mute);font-weight:600}
.grid{display:grid;gap:12px}.g4{grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}.g2{grid-template-columns:repeat(auto-fit,minmax(min(100%,430px),1fr));align-items:start}
.card{border:1px solid var(--line);background:var(--surface);border-radius:16px;padding:14px 16px;animation:rise .45s cubic-bezier(.2,0,0,1) both}
.card .k{font-size:11px;letter-spacing:1px;text-transform:uppercase;color:var(--mute)}
.card .v{font-size:34px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.15}
.card small{display:block;color:var(--mute);font-size:12px}
.bad{color:var(--block)}.good{color:var(--user)}.warn{color:var(--unt)}
.bar{height:8px;border-radius:4px;background:#1b2740;margin:8px 0 4px;overflow:hidden}.bar i{display:block;height:100%;border-radius:4px;width:0;transition:width 1s cubic-bezier(.2,0,0,1)}
table{width:100%;border-collapse:collapse;font-size:13.5px}th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left}
th{font-size:11px;letter-spacing:1px;text-transform:uppercase;color:var(--mute);font-weight:600}
table.atk{table-layout:fixed}table.atk th:first-child{width:34%}th.c{text-align:center}td.c{text-align:center;vertical-align:middle}
.sub{display:block;min-height:16px;margin-top:3px;font-size:11.5px;color:var(--mute);white-space:nowrap}
.cell{display:inline-block;border-radius:8px;padding:2px 10px;font-weight:700;font-size:12px;letter-spacing:.4px}
.cell.leak{background:#3a1416;color:#fecaca;border:1px solid var(--block)}.cell.ok{background:#0f2a1c;color:#bbf7d0;border:1px solid #1f7a45}.cell.part{background:#33200f;color:#fed7aa;border:1px solid #8a4a1d}
.note{border:1px dashed var(--line2);border-radius:14px;padding:12px 16px;color:var(--mute);font-size:13.5px;background:#0a1020}
.note b{color:var(--text)}
@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""


def _pct(x: dict[str, Any]) -> str:
    return f"{100 * x['p']:.1f}%"


def _ci(x: dict[str, Any]) -> str:
    return f"{x['k']}/{x['n']} · 95% CI {100 * x['lo']:.1f}–{100 * x['hi']:.1f}%"


def load_results() -> Optional[dict[str, Any]]:
    try:
        return json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    except Exception:
        return None


def results_html(r: dict[str, Any]) -> str:
    d = r["defences"]
    cards = []
    for key, label in (("D0", "Undefended"), ("D1", "Keyword filter"), ("D2", "Black Onyx rules")):
        if key not in d:
            continue
        a = d[key]["asr_all"]
        cls = "good" if a["p"] == 0 else "bad"
        color = "var(--user)" if a["p"] == 0 else "var(--block)"
        cards.append(f'<div class="card"><div class="k">Attack success · {key} {label}</div>'
                     f'<div class="v {cls}">{_pct(a)}</div><div class="bar"><i data-w="{100 * a["p"]:.1f}" '
                     f'style="background:{color}"></i></div><small>{_ci(a)}</small></div>')
    bu, ob, d2 = d["D2"]["bu"], d["D2"]["overblock"], d["D2"]
    cards.append(f'<div class="card"><div class="k">Legit tasks completed (D2)</div><div class="v good">{bu["k"]}/{bu["n"]}</div>'
                 f'<div class="bar"><i data-w="{100 * bu["p"]:.1f}" style="background:var(--user)"></i></div>'
                 f'<small>overblocking {ob["k"]}/{ob["n"]} · false alerts {d2["false_alerts"]}</small></div>')
    heads = "".join(f'<th class="c">{k}<br><span style="text-transform:none;letter-spacing:0">{html.escape(d[k]["name"])}</span></th>'
                    for k in d)
    rows = []
    for a in r["attacks"]:
        tds = []
        for k in d:
            c = a["cells"][k]
            if c["leaked"]:
                txt, cls = "LEAK", "leak"
            elif c["var_leaks"]:
                txt, cls = "blocked*", "part"
            else:
                txt, cls = "blocked", "ok"
            extra = f'<span class="sub">+{c["var_leaks"]}/{c["var_n"]} variants leaked</span>' if c["var_n"] else '<span class="sub">&nbsp;</span>'
            tds.append(f'<td class="c"><span class="cell {cls}">{txt}</span>{extra}</td>')
        rows.append(f'<tr><td><b>{a["id"]}</b> {html.escape(a["desc"])}</td>{"".join(tds)}</tr>')
    inv = r["invariance"]
    lat = (f'Rule engine (policy gate): mean <b>{d2["gate_mean_ms"]:.3f} ms</b>, p95 <b>{d2["gate_p95_ms"]:.3f} ms</b> per tool call '
           f'(target &lt; 5 ms, measured on this machine).')
    sent = html.escape(str(r.get("sentinel", "")))
    body = f"""
<div class="note" style="margin-bottom:12px"><b>How to read this.</b> Every defence faced the same {r['n_attacks']} attacks plus {r['n_variants']} reworded variants.
<b>Attack success</b> means the attacker's goal really happened in the mock world, so lower is better. <b>Legit tasks completed</b> shows that normal work was not blocked, so higher is better.</div>
<div class="grid g4">{''.join(cards)}</div>
<div class="card" style="margin-top:12px"><h2>Every attack, every defence</h2>
<div style="overflow:auto"><table class="atk"><tr><th>Attack</th>{heads}</tr>{''.join(rows)}</table></div>
<small style="color:var(--mute)">"+k/n variants leaked" counts the reworded versions of that attack that still got through. * = the base attack was blocked but some rewordings were not.
<br>D3 column in this table used <b>{sent}</b>: the rules decide everything, so D3 equals D2 here. The live demo runs the real Laya sentinel.</small></div>
<div class="grid g2" style="margin-top:12px">
 <div class="card"><h2>Rewording does not matter</h2><div class="v good">{_pct(inv)}</div>
  <small>{_ci(inv)} · variants whose policy decision equals the base attack's decision (D2). Decisions depend on where a value came from, not on what the text says.</small></div>
 <div class="card"><h2>Latency</h2><small style="font-size:14px;color:var(--text)">{lat}</small>
  <small style="margin-top:6px">The Laya sentinel is timed separately and is advisory (it never blocks).</small></div>
</div>
<div class="note" style="margin-top:12px"><b>Honest limits.</b> The attacker-following agent is a simulation of a compliant LLM, not a real one.
Numbers are for this suite only ({r['n_tasks']} legitimate tasks, {r['n_attacks']} base attacks, {r['n_variants']} generated variants, seed {r['seed']}).
Black Onyx does not claim a poisoned page cannot make a summary misleading, or protect against implicit flows. Laya is advisory; the rules do the blocking.
Report hash <code>{html.escape(r['hash'])}</code> (identical on repeat runs).</div>
<script>
requestAnimationFrame(()=>requestAnimationFrame(()=>document.querySelectorAll('.bar i[data-w]').forEach(i=>i.style.width=i.dataset.w+'%')));
</script>"""
    return f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><style>{BASE_CSS}</style>{body}"


def howitworks_html() -> str:
    body = """
<div class="grid g2">
 <div class="card"><h2>1 · Trust levels</h2>
  <p style="margin:0 0 10px;color:var(--mute)">Every value carries <b style="color:var(--text)">where it came from</b> and <b style="color:var(--text)">how far it can be trusted</b>.</p>
  <div class="lv" style="--c:var(--user)"><b>USER</b><span>Text you typed in the request.</span></div>
  <div class="lv" style="--c:var(--ver)"><b>VERIFIED</b><span>Passed a validated lookup (payee list, contacts, doc index, ledger cap).</span></div>
  <div class="lv" style="--c:var(--unt)"><b>UNTRUSTED</b><span>Anything a tool returned: email, web page, file, search result.</span></div>
 </div>
 <div class="card"><h2>2 · Labels travel with the data</h2>
  <svg viewBox="0 0 450 150" style="width:100%;height:auto" role="img" aria-label="Two untrusted values joined stay untrusted">
   <g font-family="Segoe UI,sans-serif" font-size="12">
    <rect x="8" y="14" width="130" height="38" rx="10" fill="#33200f" stroke="#fb923c"/><text x="22" y="38" fill="#e6eefc">email#7 "billing@ev"</text>
    <rect x="8" y="88" width="130" height="38" rx="10" fill="#33200f" stroke="#fb923c"/><text x="22" y="112" fill="#e6eefc">email#9 "il.co"</text>
    <path d="M140,33 C190,33 190,70 232,70" stroke="#fb923c" fill="none" stroke-width="2"/><path d="M140,107 C190,107 190,70 232,70" stroke="#fb923c" fill="none" stroke-width="2"/>
    <rect x="234" y="48" width="86" height="44" rx="10" fill="#111b30" stroke="#2a3a5c"/><text x="246" y="74" fill="#e6eefc">concat()</text>
    <path d="M322,70 L350,70" stroke="#fb923c" stroke-width="2"/>
    <rect x="352" y="48" width="92" height="44" rx="10" fill="#33200f" stroke="#fb923c"/><text x="362" y="68" fill="#e6eefc" font-size="11.5">UNTRUSTED</text><text x="362" y="83" fill="#8ea0ba" font-size="10">from EMAIL</text>
   </g></svg>
  <p style="margin:6px 0 0;color:var(--mute)">Sources are the union of the inputs and trust is the lowest input trust. Slicing, joining, decoding and summarising cannot launder a label.</p>
 </div>
 <div class="card"><h2>3 · Control vs data</h2>
  <table><tr><th>Argument</th><th>Kind</th><th>May come from</th></tr>
   <tr><td><code>send_email.to</code></td><td><span class="cell leak">control</span></td><td>You, or your contacts</td></tr>
   <tr><td><code>send_email.body</code></td><td><span class="cell ok">data</span></td><td>Anything (even untrusted)</td></tr>
   <tr><td><code>transfer_money.account</code></td><td><span class="cell leak">control</span></td><td>You, or the payee list</td></tr>
   <tr><td><code>read_file.path</code></td><td><span class="cell leak">control</span></td><td>You, or the doc index</td></tr>
  </table>
  <p style="margin:8px 0 0;color:var(--mute)">Untrusted text may fill the payload. It can never choose a destination or action. This is why legitimate work is not blocked.</p>
 </div>
 <div class="card"><h2>4 · The plan is fixed first</h2>
  <p style="margin:0;color:var(--mute)">The call sequence comes from your request alone, before any tool runs. An injected sentence cannot add, remove or reorder calls. Any call outside the plan is denied with an alert.</p>
  <div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap;align-items:center"><span class="chip">read_inbox</span>›<span class="chip">send_email</span><span style="flex:1"></span><span class="chip" style="border-color:var(--block);color:#fecaca">read_file /hr/salaries.xlsx ✕ off-plan</span></div>
 </div>
 <div class="card"><h2>5 · Validated declassifiers</h2>
  <p style="margin:0 0 6px;color:var(--mute)">The only way trust goes up. Small, deterministic, logged. They return data from a trusted table, never the untrusted input itself.</p>
  <span class="chip">payee_lookup</span> <span class="chip">contact_lookup</span> <span class="chip">doc_resolve</span> <span class="chip">amount_check ≤ ledger</span> <span class="chip">mailbox_ref</span>
 </div>
 <div class="card"><h2>6 · Laya: a second opinion</h2>
  <p style="margin:0;color:var(--mute)">A small local model scores whether each call fits your request. It can raise a warning on an allowed call. It <b style="color:var(--text)">never</b> relaxes a rule. Offline, CPU, English checkpoint. Accuracy is reported honestly in the Results tab.</p>
 </div>
</div>
<div class="note" style="margin-top:12px"><b>Guarantee claimed:</b> untrusted data cannot choose a destination or an argument the policy reserves for USER or VERIFIED data, provided the orchestrator, policy file, validators and tool registry are correct.
<b>Not claimed:</b> that a poisoned page cannot mislead a summary's wording, protection against implicit flows, or that Laya is accurate on its own.</div>
<style>.lv{display:flex;gap:12px;align-items:center;border:1px solid var(--c);border-radius:12px;padding:8px 12px;margin-bottom:8px;background:color-mix(in srgb,var(--c) 10%,transparent)}
.lv b{color:var(--c);min-width:118px;letter-spacing:.5px}.lv span{color:var(--text);font-size:13.5px}
.chip{border:1px solid var(--line2);background:#0b1220;border-radius:99px;padding:2px 10px;font-size:12.5px;font-family:var(--mono);display:inline-block;margin:2px 0}
code{font-family:var(--mono);font-size:12.5px;color:var(--cyan)}</style>"""
    return f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><style>{BASE_CSS}</style>{body}"
