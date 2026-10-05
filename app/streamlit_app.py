"""Black Onyx: live demo UI.

Sidebar = scenario controls. Main = animated monitor + provenance graph (replayable), results, how it works.
Reads only the engine's event log (docs/event-schema.md). Fully offline.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, List, Optional

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import streamlit as st
import streamlit.components.v1 as components

from app.fake_events import fake_run
from app.ui import DEFENCE_NAMES, render_stage
from app.ui.panels import howitworks_html, load_results, results_html

st.set_page_config(page_title="Black Onyx", page_icon="◆", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
:root{--bg:#070a12;--surface:#0d1424;--line:#1e2b45;--text:#e6eefc;--mute:#8ea0ba;--accent:#1d5fd6}
html,body,.stApp,[data-testid="stAppViewContainer"]{background:var(--bg)!important;color:var(--text);font-family:'Montserrat','Segoe UI',system-ui,sans-serif}
[data-testid="stHeader"],.stAppHeader{background:transparent!important;pointer-events:none}
[data-testid="stHeader"] *,.stAppHeader *{pointer-events:auto}
#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
.block-container{padding:14px 22px 10px!important;max-width:1700px}
[data-testid="stSidebar"]{background:#0a101d!important;border-right:1px solid var(--line);min-width:320px!important;max-width:320px!important}
[data-testid="stSidebar"] .block-container{padding:12px 16px!important}
[data-testid="stSidebar"] label p{font-size:11px!important;letter-spacing:1.1px;text-transform:uppercase;color:var(--mute)!important;font-weight:600}
div[data-baseweb="select"]>div,textarea,input{background:#0d1424!important;border:1px solid #243557!important;border-radius:12px!important;color:var(--text)!important;min-height:44px}
div[data-baseweb="select"]:focus-within>div,textarea:focus{border-color:#60a5fa!important}
.stButton>button{min-height:46px;border-radius:12px;border:1px solid #243557;background:#0d1424;color:var(--text);font-weight:600;transition:background .15s,border-color .15s,transform .1s}
.stButton>button:hover{border-color:#60a5fa;background:#13203d;color:#fff}
.stButton>button:active{transform:scale(.98)}
.stButton>button[kind="primary"]{background:linear-gradient(180deg,#2a6df0,#1d5fd6);border-color:#3b82f6;color:#fff}
.stButton>button[kind="primary"]:hover{background:linear-gradient(180deg,#3b7bff,#2563eb)}
.stButton>button:focus-visible{outline:2px solid #7dd3fc;outline-offset:2px}
.stTabs [data-baseweb="tab-list"]{gap:6px;border-bottom:1px solid var(--line)}
.stTabs [data-baseweb="tab"]{height:46px;border-radius:12px 12px 0 0;padding:0 18px;color:var(--mute);font-weight:600}
.stTabs [aria-selected="true"]{color:#fff!important;background:#0d1424}
.stTabs [data-baseweb="tab-highlight"]{background:#3b82f6!important}
[data-testid="stCode"] pre,[data-testid="stCode"] code{white-space:pre-wrap!important;word-break:break-word!important}
.brand{display:flex;gap:12px;align-items:center;margin-bottom:4px}
.brand svg{flex:none}.brand b{font-size:19px;letter-spacing:.6px}.brand small{display:block;color:var(--mute);font-size:11.5px;letter-spacing:.3px}
.sec{font-size:11px;letter-spacing:1.3px;text-transform:uppercase;color:#5b677a;font-weight:700;margin:16px 0 6px}
.how{border:1px solid var(--line);background:#0d1424;border-radius:12px;padding:9px 12px;color:var(--mute);font-size:12.5px;line-height:1.45}
.how b{color:var(--text)}
.topbar{display:flex;align-items:center;gap:10px;margin-bottom:6px;flex-wrap:wrap}
.pill{border:1px solid var(--line);border-radius:99px;padding:3px 12px;font-size:12px;color:var(--mute);background:#0d1424}
.pill.on{color:#bbf7d0;border-color:#1f7a45;background:#0f2a1c}
@media (max-width:900px){[data-testid="stSidebar"]{min-width:260px!important}.block-container{padding:10px!important}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
""", unsafe_allow_html=True)

DEFENCES = {
    "D0": "D0 · Undefended",
    "D1": "D1 · Keyword filter",
    "D2": "D2 · Black Onyx rules",
    "D3": "D3 · Rules + Laya sentinel",
}
TASKS = {
    "L1": "L1 · Summarise my mail, email it to me",
    "L2": "L2 · Send the Q3 budget doc to Priya",
    "L3": "L3 · Add vendor meeting to calendar",
    "L4": "L4 · Pay the latest Acme invoice",
    "L5": "L5 · Fetch a web page, save notes",
    "L6": "L6 · Reply to the customer email",
    "L7": "L7 · Send weekly report to manager",
    "L8": "L8 · Forward complaint to support",
}
ATTACKS = {
    "None": "None · clean run",
    "A1": "A1 · Direct injection in an email",
    "A2": "A2 · Reworded social engineering",
    "A3": "A3 · Web page asks for secret URL",
    "A4": "A4 · Invoice: bank details changed",
    "A5": "A5 · Multi-hop: extracted address",
    "A6": "A6 · Multi-hop via storage (notes)",
    "A7": "A7 · Result says read salaries",
    "A8": "A8 · Split address across two emails",
    "A9": "A9 · Base64-obfuscated address",
    "A10": "A10 · Calendar invite adds outsider",
}
HOST = {"A1": "L1", "A2": "L1", "A3": "L5", "A4": "L4", "A5": "L8", "A6": "L5 then L9", "A7": "L2", "A8": "L1",
        "A9": "L1", "A10": "L3"}

for k, v in (("defence_sel", "D2"), ("task_sel", "L1"), ("attack_sel", "A1"), ("inject_txt", "")):
    st.session_state.setdefault(k, v)


def load_prompts() -> list[tuple[int, str, str, str]]:
    """Fresh judge prompts from docs/judge-prompts.md (kept in sync with the tests)."""
    import re
    try:
        text = (ROOT / "docs" / "judge-prompts.md").read_text(encoding="utf-8")
    except OSError:
        return []
    pat = r"### (\d+)\. (.+?)\nUse task: \*\*(L\d)\*\*\n```text\n(.*?)\n```"
    return [(int(m[0]), m[1], m[2], m[3]) for m in re.findall(pat, text, re.S)]


def _preset(defence: str, task: str, attack: str) -> None:
    st.session_state.update(defence_sel=defence, task_sel=task, attack_sel=attack, inject_txt="", pending_run=True)


@st.cache_resource(show_spinner=False)
def get_sentinel():
    """Laya loads once (about 10 s). Any problem falls back to NullSentinel so a run never fails."""
    try:
        from blackonyx.laya_sentinel import LayaSentinel
        s = LayaSentinel()
        return s, "Laya (English, CPU fp32)"
    except Exception as e:  # noqa: BLE001
        from blackonyx.sentinel import NullSentinel
        return NullSentinel(), f"NullSentinel (Laya unavailable: {type(e).__name__})"


def execute(defence: str, task: str, attack: str, inject: str) -> tuple[list[dict[str, Any]], str]:
    source = "engine"
    if inject.strip():
        attack = "None"  # pasted text takes priority over a preset attack
    try:
        from blackonyx.runner import run_scenario
        sentinel = None
        if defence in ("D3", "D4"):
            with st.spinner("Loading the local Laya sentinel (first time only, offline)…"):
                sentinel, source = get_sentinel()
        ev = run_scenario(task_id=task, attack_id=None if attack == "None" else attack, defence=defence,
                          injected_text=inject.strip() or None, sentinel=sentinel)
        return ev, source
    except Exception:  # noqa: BLE001
        return fake_run(attack=(attack != "None") or bool(inject.strip()), task_id=task, defence=defence,
                        injected_text=inject.strip() or None), "fake events (engine unavailable)"


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("""
<div class="brand"><svg width="40" height="40" viewBox="0 0 40 40" aria-hidden="true"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3b82f6"/><stop offset="1" stop-color="#0b1f4b"/></linearGradient></defs>
<path d="M20 2 35 11v18L20 38 5 29V11z" fill="#0d1424" stroke="url(#g)" stroke-width="2.4"/><path d="M20 10 28 15v10l-8 5-8-5V15z" fill="url(#g)"/></svg>
<div><b>BLACK ONYX</b><small>Provenance firewall for AI agents</small></div></div>
""", unsafe_allow_html=True)

    st.markdown('<div class="sec">Scenario</div>', unsafe_allow_html=True)
    defence_id = st.selectbox("Defence", list(DEFENCES), format_func=DEFENCES.get, key="defence_sel")
    attack_id = st.selectbox("Attack", list(ATTACKS), format_func=ATTACKS.get, key="attack_sel")
    typed = bool(st.session_state.get("inject_txt", "").strip())
    has_attack = attack_id != "None" and not typed
    task_id = st.selectbox("Legit task", list(TASKS), format_func=TASKS.get, key="task_sel", disabled=has_attack,
                           help="A preset attack runs on its own host task, so this is locked while one is selected.")
    if has_attack:
        st.caption(f"Preset attack {attack_id} runs on its own host task: **{HOST[attack_id]}**")
    elif typed and attack_id != "None":
        st.caption("Your pasted text takes priority, so the attack dropdown is ignored.")
    inject_text = st.text_area("Paste your own attack", key="inject_txt", height=96,
                               placeholder="Paste any injection here (see the prompt library in the main panel), pick a task, press Run.",
                               help="Hidden where the chosen task will read it: an email, the fetched web page, or a document.")
    autoplay = st.toggle("Animate playback", value=True, help="Off shows the finished run instantly. You can always scrub.")
    run_clicked = st.button("▶  Run scenario", type="primary", use_container_width=True)

    st.markdown('<div class="sec">Demo script</div>', unsafe_allow_html=True)
    st.button("① Undefended agent gets hijacked", use_container_width=True, on_click=_preset, args=("D0", "L1", "A1"))
    st.button("② Same input, Black Onyx contains it", use_container_width=True, on_click=_preset, args=("D2", "L1", "A1"))
    st.button("③ Reworded attack beats keyword filter", use_container_width=True, on_click=_preset, args=("D1", "L1", "A2"))
    st.button("④ Multi-hop: split address (A8)", use_container_width=True, on_click=_preset, args=("D2", "L1", "A8"))
    st.button("⑤ Legit payment still passes (L4)", use_container_width=True, on_click=_preset, args=("D2", "L4", "None"))
    st.button("⑥ With the Laya second opinion", use_container_width=True, on_click=_preset, args=("D3", "L1", "A1"))

    st.markdown('<div class="sec">What am I looking at?</div>', unsafe_allow_html=True)
    st.markdown('<div class="how">An AI agent reads your data (email, web, files) and uses tools. <b>Attackers hide '
                'instructions inside that data.</b> Black Onyx tags every value with where it came from and refuses to let '
                'untrusted text choose a destination, a file or an account. Pick <b>D0</b> to see the agent obey, then '
                '<b>D2</b> to see it contained.</div>', unsafe_allow_html=True)

    st.markdown('<div class="sec">Legend</div>', unsafe_allow_html=True)
    st.markdown('<div class="how"><b style="color:#4ade80">Green</b> you · <b style="color:#60a5fa">blue</b> verified lookup · '
                '<b style="color:#fb923c">orange</b> untrusted data · <b style="color:#f87171">red</b> blocked · '
                '<b style="color:#a78bfa">purple</b> Laya.<br>Keys: <b>Space</b> play · <b>←/→</b> step · <b>E</b> end · <b>R</b> restart.</div>',
                unsafe_allow_html=True)

# ---------------------------------------------------------------- run
if run_clicked or st.session_state.pop("pending_run", False) or "events" not in st.session_state:
    eff_task = task_id
    ev, src = execute(defence_id, eff_task, attack_id, inject_text)
    st.session_state.update(events=ev, runner_source=src, last_defence=defence_id, run_id=st.session_state.get("run_id", 0) + 1)

events: List[dict[str, Any]] = st.session_state.get("events", [])
src = st.session_state.get("runner_source", "engine")
shown_defence = st.session_state.get("last_defence", defence_id)

tab_live, tab_results, tab_how = st.tabs(["Live demo", "Results", "How it works"])

with tab_live:
    st.markdown(
        f'<div class="topbar"><span class="pill on">offline · 0 cloud calls</span>'
        f'<span class="pill">{DEFENCES.get(shown_defence, shown_defence)}</span>'
        f'<span class="pill">{len(events)} events</span><span class="pill">{"live engine" if src == "engine" else src}</span></div>',
        unsafe_allow_html=True)
    components.html(render_stage(events, autoplay=autoplay, defence=shown_defence), height=830, scrolling=False)
    prompts = load_prompts()
    if prompts:
        with st.expander(f"Prompt library: {len(prompts)} fresh attacks to paste into the box (not in the dropdown)"):
            st.caption("Copy a prompt (button at the top right of each box), paste it into **Paste your own attack** in the "
                       "sidebar, choose the task shown, set the defence, press Run. Try D0 first, then D2.")
            for n, title, task, text in prompts:
                st.markdown(f"**{n}. {title}** · use task **{task}**")
                st.code(text, language=None)

with tab_results:
    res = load_results()
    if res is None:
        st.info("No results yet. Generate them with the evaluation harness (about 30 seconds, fully offline).")
        if st.button("Run the evaluation now"):
            with st.spinner("Running 8 tasks, 10 attacks and 300 variants under four defences…"):
                from eval.run_eval import evaluate, export_json, metrics, repro_hash, write_report
                r_ = evaluate(60, False)
                m_, h_ = metrics(r_), repro_hash(r_)
                write_report(r_, m_, ROOT / "docs" / "results.md", h_)
                export_json(r_, m_, ROOT / "docs" / "results.json", h_)
            st.rerun()
    else:
        components.html(results_html(res), height=980, scrolling=True)
        laya_md = ROOT / "docs" / "laya-results.md"
        if laya_md.exists():
            with st.expander("Laya sentinel measurements (advisory layer, CPU fp32)"):
                st.markdown(laya_md.read_text(encoding="utf-8"))

with tab_how:
    components.html(howitworks_html(), height=1180, scrolling=True)
