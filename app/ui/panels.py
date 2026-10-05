"""Results and Explain panels (self-contained HTML, offline). Flat, restrained, evidence-first."""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
RESULTS_JSON = ROOT / "docs" / "results.json"

BASE_CSS = """
:root{--bg:#070A0F;--p:#0D121A;--p2:#111823;--bd:#1B2532;--bd2:#263243;--tx:#E6EAF0;--t2:#8C96A6;--t3:#5C6675;
--blue:#4F8CFF;--green:#35D07F;--amber:#E7A33D;--red:#F05D67;
--font:Inter,'Segoe UI',system-ui,sans-serif;--mono:Consolas,'Cascadia Mono',ui-monospace,monospace}
*{box-sizing:border-box}html,body{margin:0;background:transparent;color:var(--tx);font:13px/1.55 var(--font);overflow-x:hidden}
.lbl{font-size:11px;font-weight:500;letter-spacing:.8px;text-transform:uppercase;color:var(--t3)}
h2{margin:0 0 8px;font-size:11px;font-weight:500;letter-spacing:.8px;text-transform:uppercase;color:var(--t3)}
.panel{background:var(--p);border:1px solid var(--bd);border-radius:6px;padding:14px 16px;margin-bottom:12px}
.metrics{display:flex;flex-wrap:wrap;gap:0;margin-bottom:12px;background:var(--p);border:1px solid var(--bd);border-radius:6px}
.metrics>div{flex:1 1 200px;padding:14px 18px;border-left:1px solid var(--bd)}
.metrics>div:first-child{border-left:0}
.metrics .v{font:600 26px/1.1 var(--mono);font-variant-numeric:tabular-nums;margin:4px 0 2px}
.metrics small{color:var(--t2);font-size:12px}
.red{color:var(--red)}.green{color:var(--green)}.amber{color:var(--amber)}.dim{color:var(--t2)}
table{width:100%;border-collapse:collapse;table-layout:fixed}
th,td{padding:8px 10px;border-top:1px solid var(--bd);vertical-align:middle}
th{border-top:0;text-align:left;font-size:11px;font-weight:500;letter-spacing:.6px;text-transform:uppercase;color:var(--t3)}
th.c,td.c{text-align:center}
table.atk th:first-child{width:36%}
.st{font-weight:600;font-size:12px;letter-spacing:.4px}.st i{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:6px;vertical-align:0}
.st.leak{color:var(--red)}.st.leak i{background:var(--red)}
.st.ok{color:var(--green)}.st.ok i{background:var(--green)}
.st.part{color:var(--amber)}.st.part i{background:var(--amber)}
.sub{display:block;min-height:15px;font-size:11.5px;color:var(--t3);font-weight:400;letter-spacing:0}
.note{color:var(--t2);font-size:12.5px}.note b{color:var(--tx);font-weight:600}
code,.mono{font-family:var(--mono);font-size:12px}
dl.def{display:grid;grid-template-columns:120px 1fr;gap:10px 16px;margin:0}
dl.def dt{color:var(--t3);font-size:11px;letter-spacing:.8px;text-transform:uppercase;padding-top:2px}
dl.def dd{margin:0}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:12px;align-items:start}
.two .panel{margin-bottom:0}
.tag{font-family:var(--mono);font-size:12px;color:var(--t2)}
.lv{display:grid;grid-template-columns:100px 1fr;gap:12px;padding:8px 0;border-top:1px solid var(--bd)}
.lv:first-of-type{border-top:0}.lv b{font-weight:600}
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


def _page(body: str) -> str:
    return f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><style>{BASE_CSS}</style>{body}"


def results_html(r: dict[str, Any]) -> str:
    d = r["defences"]
    sent = html.escape(str(r.get("sentinel", "")))
    if str(r.get("sentinel", "")).startswith("Laya"):
        nv = (d.get("D3", {}).get("asr_var") or {}).get("n")
        sub = f" on {nv} of the variants (a deterministic subset, because it takes about 0.3 s per call)" if nv and nv < 300 else " on every variant"
        laya_note = (f"D3 and D4 used the real Laya sentinel{sub}. "
                     "D4 (Laya alone, no rules) also blocks legitimate work, which is why the rules do the blocking.")
    else:
        laya_note = f"D3 in this table ran with <b>{sent}</b>, so it equals D2; the live demo uses the real Laya sentinel."
    d2, bu, ob = d["D2"], d["D2"]["bu"], d["D2"]["overblock"]
    metrics = []
    for key, label in (("D0", "Undefended"), ("D1", "Keyword filter"), ("D2", "Black Onyx rules")):
        if key not in d:
            continue
        a = d[key]["asr_all"]
        cls = "green" if a["p"] == 0 else "red"
        metrics.append(f'<div><div class="lbl">Attack success · {key} {label}</div><div class="v {cls}">{_pct(a)}</div><small>{_ci(a)}</small></div>')
    metrics.append(f'<div><div class="lbl">Legitimate tasks completed · D2</div><div class="v green">{bu["k"]}/{bu["n"]}</div>'
                   f'<small>{ob["k"]}/{ob["n"]} sensitive calls wrongly blocked · {d2["false_alerts"]} false alerts</small></div>')
    heads = "".join(f'<th class="c">{k}<br><span style="text-transform:none;letter-spacing:0;color:var(--t2)">{html.escape(d[k]["name"])}</span></th>' for k in d)
    rows = []
    for a in r["attacks"]:
        tds = []
        for k in d:
            c = a["cells"][k]
            txt, cls = ("LEAK", "leak") if c["leaked"] else (("BLOCKED*", "part") if c["var_leaks"] else ("BLOCKED", "ok"))
            extra = f'<span class="sub">{c["var_leaks"]}/{c["var_n"]} variants leaked</span>' if c["var_n"] else '<span class="sub">&nbsp;</span>'
            tds.append(f'<td class="c"><span class="st {cls}"><i></i>{txt}</span>{extra}</td>')
        rows.append(f'<tr><td><b>{a["id"]}</b> <span class="dim">{html.escape(a["desc"])}</span></td>{"".join(tds)}</tr>')
    inv = r["invariance"]
    body = f"""
<p class="note" style="margin:0 0 12px">{r['n_attacks']} attacks and {r['n_variants']} reworded variants against every defence. Attack success means the attacker's goal happened in the mock world (lower is better).</p>
<div class="metrics">{''.join(metrics)}</div>
<div class="panel"><h2>Outcome by attack and defence</h2>
<div style="overflow:auto"><table class="atk"><tr><th>Attack</th>{heads}</tr>{''.join(rows)}</table></div>
<p class="note" style="margin:10px 0 0">* base attack blocked, some rewordings were not. {laya_note}</p></div>
<div class="two">
 <div class="panel"><h2>Invariance under rewording</h2><div class="mono" style="font-size:22px;font-weight:600">{_pct(inv)}</div>
  <p class="note" style="margin:4px 0 0">{_ci(inv)}. Variants whose policy decision equals the base attack's decision (D2).</p></div>
 <div class="panel"><h2>Policy evaluation</h2><div class="mono" style="font-size:22px;font-weight:600">{max(1, round(d2['gate_mean_ms'] * 1000))} µs <span class="dim" style="font-size:13px">mean</span></div>
  <p class="note" style="margin:4px 0 0">p95 {max(1, round(d2['gate_p95_ms'] * 1000))} µs per tool call, measured on this machine. Laya is timed separately and is advisory.</p></div>
</div>
<div class="panel" style="margin-top:12px"><h2>Limits</h2><p class="note" style="margin:0">The attacker is a simulation of a compliant LLM, not a real one. Results apply to this suite
({r['n_tasks']} tasks, {r['n_attacks']} attacks, {r['n_variants']} variants, seed {r['seed']}). Black Onyx does not claim a poisoned page cannot mislead a summary's wording, or protect against implicit flows.
Report hash <code>{html.escape(r['hash'])}</code>, identical on repeat runs.</p></div>"""
    return _page(body)


def howitworks_html() -> str:
    body = """
<div class="two">
 <div class="panel"><h2>Trust levels</h2>
  <div class="lv"><b>USER</b><span>Typed by the user in the request.</span></div>
  <div class="lv"><b style="color:var(--blue)">VERIFIED</b><span>Resolved from a trusted table: payee list, contacts, document index, ledger cap.</span></div>
  <div class="lv"><b class="amber">UNTRUSTED</b><span>Anything a tool returned: email, web page, file, search result.</span></div></div>
 <div class="panel"><h2>Propagation</h2>
  <p class="note" style="margin:0">Every operation (concat, slice, split, join, decode, extract, summarise) returns a value whose sources are the union of its inputs and whose trust is the lowest input trust.
  A label cannot be dropped by reformatting, joining or decoding.</p>
  <p class="mono dim" style="margin:10px 0 0">concat(email#7, email#9) → EMAIL · UNTRUSTED</p></div>
 <div class="panel"><h2>Control and data arguments</h2>
  <table><tr><th>Argument</th><th>Kind</th><th>Allowed origin</th></tr>
   <tr><td class="mono">send_email.to</td><td class="red">control</td><td>user, contacts</td></tr>
   <tr><td class="mono">send_email.body</td><td class="dim">data</td><td>any</td></tr>
   <tr><td class="mono">transfer_money.account</td><td class="red">control</td><td>user, payee list</td></tr>
   <tr><td class="mono">read_file.path</td><td class="red">control</td><td>user, document index</td></tr></table>
  <p class="note" style="margin:8px 0 0">Untrusted text may fill the payload. It cannot select a destination or an action.</p></div>
 <div class="panel"><h2>Fixed plan</h2>
  <p class="note" style="margin:0">The call sequence is derived from the request alone, before any tool runs. Calls outside it are denied.</p>
  <p class="mono dim" style="margin:10px 0 0">read_inbox → send_email<br><span class="red">read_file /hr/salaries.xlsx  ✕ not in plan</span></p></div>
 <div class="panel"><h2>Validated declassifiers</h2>
  <p class="note" style="margin:0">The only way trust rises. Each is deterministic, logged, and returns data from a trusted table, never the untrusted input.</p>
  <p class="tag" style="margin:8px 0 0">payee_lookup · contact_lookup · doc_resolve · amount_check · mailbox_ref</p></div>
 <div class="panel"><h2>Laya sentinel</h2>
  <p class="note" style="margin:0">A local model gives each call a Fit percentage: how well it matches what the user asked (100% = a clear match, low = unusual for this request). It can warn on an allowed call. It never relaxes a rule. Offline, CPU, English checkpoint.</p></div>
</div>
<div class="panel" style="margin-top:12px"><h2>Guarantee</h2>
 <p class="note" style="margin:0">Untrusted data cannot choose a destination or an argument the policy reserves for USER or VERIFIED data, provided the orchestrator, policy file, validators and tool registry are correct.
 <b>Not claimed:</b> that a poisoned page cannot mislead a summary's wording, protection against implicit flows, or that Laya is accurate on its own.</p></div>"""
    return _page(body)
