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
:root{--bg:#070A0F;--p:#0D121A;--p2:#111823;--bd:#1B2532;--bd2:#263243;--tx:#E6EAF0;--t2:#8C96A6;--t3:#5C6675;--blue:#4F8CFF}
html,body,.stApp,[data-testid="stAppViewContainer"]{background:var(--bg)!important;color:var(--tx);font-family:Inter,'Segoe UI',system-ui,sans-serif;font-size:13px}
[data-testid="stHeader"],.stAppHeader{background:transparent!important;pointer-events:none}
[data-testid="stHeader"] *,.stAppHeader *{pointer-events:auto}
#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
.block-container{padding:12px 20px 8px!important;max-width:1700px}
[data-testid="stSidebar"]{background:var(--p)!important;border-right:1px solid var(--bd);min-width:280px!important;max-width:280px!important}
[data-testid="stSidebar"] .block-container{padding:16px 16px!important}
[data-testid="stSidebar"] label p{font-size:11px!important;font-weight:500;letter-spacing:.8px;text-transform:uppercase;color:var(--t3)!important}
div[data-baseweb="select"]>div,textarea,input{background:var(--bg)!important;border:1px solid var(--bd2)!important;border-radius:4px!important;color:var(--tx)!important;min-height:38px;font-size:13px}
div[data-baseweb="select"]:focus-within>div,textarea:focus{border-color:var(--blue)!important}
textarea{font-family:Consolas,'Cascadia Mono',monospace!important;font-size:12px!important}
.stButton>button{min-height:38px;border-radius:4px;border:1px solid var(--bd2);background:var(--bg);color:var(--tx);font-weight:500;font-size:13px;transition:background .12s,border-color .12s}
.stButton>button:hover{border-color:var(--t3);background:var(--p2);color:var(--tx)}
.stButton>button:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
.stButton>button[kind="primary"]{background:var(--blue);border-color:var(--blue);color:#06101f;font-weight:600}
.stButton>button[kind="primary"]:hover{background:#6aa0ff;border-color:#6aa0ff;color:#06101f}
.stButton>button[kind="secondary"]{justify-content:flex-start;text-align:left}
.stButton>button[kind="secondary"] div,.stButton>button[kind="secondary"] p{justify-content:flex-start!important;text-align:left!important;width:100%}
.stTabs [data-baseweb="tab-list"]{gap:4px;border-bottom:1px solid var(--bd)}
.stTabs [data-baseweb="tab"]{height:40px;padding:0 14px;color:var(--t2);font-weight:500;background:transparent}
.stTabs [aria-selected="true"]{color:var(--tx)!important}
.stTabs [data-baseweb="tab-highlight"]{background:var(--blue)!important;height:2px}
[data-testid="stCode"] pre,[data-testid="stCode"] code{white-space:pre-wrap!important;word-break:break-word!important;font-size:12px!important}
[data-testid="stExpander"]{border:1px solid var(--bd)!important;border-radius:6px!important;background:var(--p)}
hr{border-color:var(--bd)!important;margin:14px 0!important}
.brand{display:flex;gap:10px;align-items:center;margin-bottom:2px}
.brand b{font-size:16px;font-weight:600;letter-spacing:.2px}.brand small{display:block;color:var(--t3);font-size:11.5px}
.sec{font-size:11px;font-weight:500;letter-spacing:.8px;text-transform:uppercase;color:var(--t3);margin:16px 0 6px}
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
<div class="brand"><svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true"><path d="M15 2 26 8.5v13L15 28 4 21.5v-13z" fill="none" stroke="#E6EAF0" stroke-width="1.6"/><path d="M15 2v26" stroke="#E6EAF0" stroke-width="1.6"/></svg>
<div><b>Black Onyx</b><small>Provenance firewall for AI agents</small></div></div>
""", unsafe_allow_html=True)

    st.markdown('<div class="sec">Scenario</div>', unsafe_allow_html=True)
    defence_id = st.selectbox("Defence", list(DEFENCES), format_func=DEFENCES.get, key="defence_sel")
    attack_id = st.selectbox("Attack", list(ATTACKS), format_func=ATTACKS.get, key="attack_sel")
    typed = bool(st.session_state.get("inject_txt", "").strip())
    has_attack = attack_id != "None" and not typed
    task_id = st.selectbox("Task", list(TASKS), format_func=TASKS.get, key="task_sel", disabled=has_attack)
    if has_attack:
        st.caption(f"{attack_id} runs on its own host task: {HOST[attack_id]}")
    elif typed and attack_id != "None":
        st.caption("Custom attack takes priority over the attack selection.")

    st.markdown('<div class="sec">Custom attack</div>', unsafe_allow_html=True)
    inject_text = st.text_area("Paste an injection", key="inject_txt", height=96, label_visibility="collapsed",
                               placeholder="Paste an injection. It is planted where the chosen task will read it (email, web page or document).")
    autoplay = st.toggle("Animate playback", value=True)
    run_clicked = st.button("Run scenario", type="primary", use_container_width=True)

    st.markdown('<div class="sec">Demo scenarios</div>', unsafe_allow_html=True)
    st.button("01  Agent is hijacked", use_container_width=True, on_click=_preset, args=("D0", "L1", "A1"))
    st.button("02  Black Onyx contains it", use_container_width=True, on_click=_preset, args=("D2", "L1", "A1"))
    st.button("03  Reworded attack, keyword filter", use_container_width=True, on_click=_preset, args=("D1", "L1", "A2"))
    st.button("04  Multi-hop: split address", use_container_width=True, on_click=_preset, args=("D2", "L1", "A8"))
    st.button("05  Legitimate payment passes", use_container_width=True, on_click=_preset, args=("D2", "L4", "None"))
    st.button("06  With Laya second opinion", use_container_width=True, on_click=_preset, args=("D3", "L1", "A1"))

# ---------------------------------------------------------------- run
if run_clicked or st.session_state.pop("pending_run", False) or "events" not in st.session_state:
    eff_task = task_id
    ev, src = execute(defence_id, eff_task, attack_id, inject_text)
    st.session_state.update(events=ev, runner_source=src, last_defence=defence_id, run_id=st.session_state.get("run_id", 0) + 1)

events: List[dict[str, Any]] = st.session_state.get("events", [])
src = st.session_state.get("runner_source", "engine")
shown_defence = st.session_state.get("last_defence", defence_id)

tab_live, tab_results, tab_how = st.tabs(["Run", "Results", "Explain"])

with tab_live:
    components.html(render_stage(events, autoplay=autoplay, defence=shown_defence), height=860, scrolling=False)
    prompts = load_prompts()
    if prompts:
        with st.expander(f"Prompt library ({len(prompts)} custom attacks)"):
            st.caption("Copy a prompt, paste it into Custom attack in the sidebar, choose the task shown and run. Compare D0 with D2.")
            for n, title, task, text in prompts:
                st.markdown(f"**{n:02d}  {title}** · task {task}")
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
