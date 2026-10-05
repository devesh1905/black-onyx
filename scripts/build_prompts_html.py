"""Build docs/judge-prompts/index.html (self-contained, copy buttons) from docs/judge-prompts.md.

    python scripts/build_prompts_html.py
"""
from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "judge-prompts.md"
OUT = ROOT / "docs" / "judge-prompts" / "index.html"

TASKS = {
    "L1": "Summarise my mail, email it to me", "L2": "Send the Q3 budget doc to Priya", "L3": "Add vendor meeting to calendar",
    "L4": "Pay the latest Acme invoice", "L5": "Fetch a web page, save notes", "L6": "Reply to the customer email",
    "L7": "Send weekly report to manager", "L8": "Forward complaint to support",
}


def parse(md: str):
    items = []
    pat = re.compile(r"### (\d+)\. (.+?)\nUse task: \*\*(L\d)\*\*\n```text\n(.*?)\n```\n?(.*?)(?=\n### |\Z)", re.S)
    for m in pat.finditer(md):
        items.append({"n": int(m.group(1)), "title": m.group(2).strip(), "task": m.group(3), "text": m.group(4),
                      "expected": re.sub(r"^Expected[^:]*:\s*", "", m.group(5).strip())})
    return items


def build() -> str:
    items = parse(SRC.read_text(encoding="utf-8"))
    cards = []
    for it in items:
        benign = "must NOT" in it["title"]
        title = it["title"].replace(" (must NOT trigger anything)", "")
        exp = html.escape(it["expected"]) if it["expected"] else ("D0 obeys the text; D2 blocks it and your task still finishes." if not benign else "")
        cards.append(f"""
<article class="card{' benign' if benign else ''}" data-s="{html.escape((title + ' ' + it['text'] + ' ' + it['task']).lower())}">
  <header>
    <span class="num">{it['n']:02d}</span>
    <h2>{html.escape(title)}</h2>
    {'<span class="tag ok">must stay quiet</span>' if benign else '<span class="tag">attack</span>'}
  </header>
  <div class="task">Use task <button class="chip" data-copy="{it['task']}" title="Copy task id">{it['task']}</button>
    <span class="tdesc">{html.escape(TASKS.get(it['task'], ''))}</span></div>
  <pre class="prompt" id="p{it['n']}">{html.escape(it['text'])}</pre>
  <p class="exp">{exp}</p>
  <div class="actions"><button class="copy" data-target="p{it['n']}">Copy prompt</button></div>
</article>""")
    return PAGE.replace("@@CARDS@@", "\n".join(cards)).replace("@@COUNT@@", str(len(items)))


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Black Onyx judge prompts</title>
<style>
:root{--bg:#070A0F;--p:#0D121A;--p2:#111823;--bd:#1B2532;--bd2:#263243;--tx:#E6EAF0;--t2:#9AA5B5;--t3:#7A8696;--blue:#4F8CFF;--green:#35D07F;--red:#F05D67;
--font:Inter,'Segoe UI',system-ui,sans-serif;--mono:Consolas,'Cascadia Mono',ui-monospace,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.55 var(--font)}
main{max-width:980px;margin:0 auto;padding:28px 20px 60px}
h1{margin:0 0 4px;font-size:26px;letter-spacing:.3px}
.sub{color:var(--t2);margin:0 0 18px;max-width:760px}
.how{background:var(--p);border:1px solid var(--bd);border-radius:6px;padding:12px 16px;margin:0 0 18px}
.how ol{margin:6px 0 0;padding-left:20px}.how li{margin:2px 0}
.bar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:0 0 16px}
input[type=search]{flex:1;min-width:220px;background:var(--p);border:1px solid var(--bd2);border-radius:4px;color:var(--tx);padding:10px 12px;font:inherit}
input[type=search]:focus{outline:2px solid var(--blue);outline-offset:1px}
button{font:inherit;color:inherit;cursor:pointer}
.btn{min-height:40px;padding:0 14px;border:1px solid var(--bd2);border-radius:4px;background:var(--p2)}
.btn:hover{border-color:var(--t3)}
.count{color:var(--t3);font-size:12px}
.grid{display:grid;gap:12px}
.card{background:var(--p);border:1px solid var(--bd);border-radius:6px;padding:14px 16px}
.card[hidden]{display:none}
.card header{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.num{font:12px var(--mono);color:var(--t3)}
.card h2{margin:0;font-size:16px;flex:1}
.tag{font-size:11px;letter-spacing:.8px;text-transform:uppercase;color:var(--t2);border:1px solid var(--bd2);border-radius:4px;padding:2px 8px}
.tag.ok{color:var(--green);border-color:#1f7a45}
.task{margin:8px 0 8px;color:var(--t2);font-size:13px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.chip{font:600 12px var(--mono);background:var(--p2);border:1px solid var(--bd2);border-radius:4px;padding:2px 9px;color:var(--tx)}
.chip:hover{border-color:var(--blue)}
.tdesc{color:var(--t3)}
.prompt{margin:0;background:#080c13;border:1px solid var(--bd);border-radius:4px;padding:12px 14px;font:13px/1.55 var(--mono);white-space:pre-wrap;overflow-wrap:anywhere;user-select:all}
.exp{margin:8px 0 0;color:var(--t2);font-size:13px}
.actions{margin-top:10px;display:flex;gap:8px}
.copy{min-height:38px;padding:0 16px;border:1px solid var(--blue);border-radius:4px;background:var(--blue);color:#06101f;font-weight:600}
.copy:hover{filter:brightness(1.1)}
.copy.done{background:#14301f;border-color:#1f7a45;color:#bbf7d0}
.chip.done{border-color:#1f7a45;color:#bbf7d0}
.toast{position:fixed;left:50%;bottom:22px;transform:translateX(-50%);background:#14301f;border:1px solid #1f7a45;color:#bbf7d0;padding:8px 16px;border-radius:4px;opacity:0;pointer-events:none;transition:opacity .2s}
.toast.show{opacity:1}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
</head>
<body>
<main>
  <h1>Judge prompts</h1>
  <p class="sub">@@COUNT@@ fresh injections that are not in the app's attack dropdown. Each one works with the task named on its card.</p>
  <div class="how"><b>How to use</b>
    <ol>
      <li>In the app, open <b>Custom attack</b> in the sidebar.</li>
      <li>Press <b>Copy prompt</b> on a card and paste it there. Pick the task shown on the card.</li>
      <li>Run with <b>D0</b> first (the agent obeys the hidden text), then <b>D2</b> (Black Onyx blocks it and the task still finishes).</li>
    </ol></div>
  <div class="bar">
    <input id="q" type="search" placeholder="Filter by keyword, task id or topic" aria-label="Filter prompts">
    <button class="btn" id="all">Copy all prompts</button>
    <span class="count" id="count"></span>
  </div>
  <section class="grid" id="grid">
@@CARDS@@
  </section>
</main>
<div class="toast" id="toast" role="status" aria-live="polite">Copied</div>
<script>
const $ = (s, r=document) => r.querySelector(s), $$ = (s, r=document) => [...r.querySelectorAll(s)];
const toast = $('#toast'); let tt;
function say(msg){ toast.textContent = msg; toast.classList.add('show'); clearTimeout(tt); tt = setTimeout(()=>toast.classList.remove('show'), 1400); }
async function copyText(text){
  try { await navigator.clipboard.writeText(text); return true; }
  catch(_){ const ta = document.createElement('textarea'); ta.value = text; ta.style.position='fixed'; ta.style.opacity='0'; document.body.appendChild(ta); ta.select();
    let ok=false; try{ ok = document.execCommand('copy'); }catch(__){} ta.remove(); return ok; }
}
function flash(btn, label){ const old = btn.dataset.label || btn.textContent; btn.dataset.label = old; btn.textContent = label; btn.classList.add('done'); setTimeout(()=>{ btn.textContent = old; btn.classList.remove('done'); }, 1200); }
$$('.copy').forEach(b => b.addEventListener('click', async () => {
  const ok = await copyText($('#'+b.dataset.target).textContent);
  flash(b, ok ? 'Copied' : 'Select the text and press Ctrl+C'); say(ok ? 'Prompt copied' : 'Copy blocked by the browser');
}));
$$('.chip').forEach(b => b.addEventListener('click', async () => { const ok = await copyText(b.dataset.copy); flash(b, ok ? 'Copied' : b.dataset.copy); }));
$('#all').addEventListener('click', async () => {
  const text = $$('.card:not([hidden]) .prompt').map(p => p.textContent).join('\\n\\n');
  const ok = await copyText(text); say(ok ? 'Copied all visible prompts' : 'Copy blocked by the browser');
});
const q = $('#q'), count = $('#count');
function filter(){ const v = q.value.trim().toLowerCase(); let n = 0;
  $$('.card').forEach(c => { const hit = !v || c.dataset.s.includes(v); c.hidden = !hit; if(hit) n++; });
  count.textContent = n + ' of ' + $$('.card').length + ' shown'; }
q.addEventListener('input', filter); filter();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    print("wrote", OUT, len(parse(SRC.read_text(encoding="utf-8"))), "prompts")
