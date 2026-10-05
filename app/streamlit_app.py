"""Black Onyx: live demo UI.

Sidebar = scenario controls. Main = animated monitor + provenance graph (replayable), results, how it works.
Reads only the engine's event log (docs/event-schema.md). Fully offline.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, List, Optional

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

try:
    from blackonyx.envfile import load_env
    load_env()   # keys from <repo parent>/.env, outside the repo
except Exception:
    pass
import streamlit as st
import streamlit.components.v1 as components

from app.fake_events import fake_run
from app.ui import DEFENCE_NAMES, render_stage
from app.ui.splash import _uri, custom_logo, splash_html
from app.ui.panels import howitworks_html, load_results, results_html

st.set_page_config(page_title="Black Onyx", page_icon="◆", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
:root{--bg:#070A0F;--p:#0D121A;--p2:#111823;--bd:#1B2532;--bd2:#263243;--tx:#E6EAF0;--t2:#9AA5B5;--t3:#7A8696;--blue:#4F8CFF}
html,body,.stApp,[data-testid="stAppViewContainer"]{background:var(--bg)!important;color:var(--tx);font-family:Inter,'Segoe UI',system-ui,sans-serif;font-size:13px}
[data-testid="stHeader"],.stAppHeader{background:transparent!important;pointer-events:none}
[data-testid="stHeader"] *,.stAppHeader *{pointer-events:auto}
#MainMenu,footer,[data-testid="stDecoration"],[data-testid="stToolbarActions"],[data-testid="stMainMenu"],[data-testid="stAppDeployButton"]{display:none!important}
[data-testid="stExpandSidebarButton"],[data-testid="stSidebarCollapsedControl"],[data-testid="collapsedControl"]{display:flex!important;visibility:visible!important}
.block-container,[data-testid="stMainBlockContainer"]{padding:2.4rem 20px 8px!important;max-width:1700px}
[data-testid="stHeader"],.stAppHeader{height:2.4rem!important;min-height:0!important}
/* the CSS-only st.markdown blocks must not take layout space (each one added a block gap above the tabs) */
[data-testid="stElementContainer"]:has(style):not(:has(.bo-splash)){display:none!important}
[data-testid="stElementContainer"]:has(.bo-splash){position:fixed!important;z-index:2147483000!important;top:0;left:0;width:0;height:0;margin:0!important;overflow:visible!important}
[data-testid="stSidebar"]{background:var(--p)!important;border-right:1px solid var(--bd)}
[data-testid="stSidebar"][aria-expanded="true"]{min-width:280px!important;max-width:280px!important}
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
.stTabs [data-baseweb="tab-list"]{display:inline-flex;gap:2px;padding:3px;background:var(--p);border:1px solid var(--bd);border-radius:6px;margin-bottom:6px}
.stTabs [data-baseweb="tab"]{height:38px;padding:0 18px;color:var(--t2);font-weight:600;font-size:14px;background:transparent;border-radius:4px}
.stTabs [aria-selected="true"]{color:#fff!important;background:var(--p2)}
.stTabs [data-baseweb="tab-highlight"]{background:var(--blue)!important;height:2px;border-radius:2px}
.stTabs [data-baseweb="tab-border"]{display:none}
.evalstrip{display:flex;flex-wrap:wrap;gap:8px;align-items:stretch;margin:2px 0 8px}
.evalstrip div{background:var(--p2);border:1px solid var(--bd);border-radius:4px;padding:8px 16px;min-width:150px}
.evalstrip b{display:block;font:600 20px/1.15 Consolas,"Cascadia Mono",monospace}.evalstrip span{font-size:11px;letter-spacing:.8px;text-transform:uppercase;color:var(--t3)}
.evalstrip .note{background:transparent;border:0;color:var(--t2);font-size:12.5px;flex:1;min-width:220px;align-self:center;padding:0 4px}
[data-testid="stCode"] pre,[data-testid="stCode"] code{white-space:pre-wrap!important;word-break:break-word!important;font-size:12px!important}
[data-testid="stExpander"]{border:1px solid var(--bd)!important;border-radius:6px!important;background:var(--p)}
hr{border-color:var(--bd)!important;margin:14px 0!important}
.brand{display:flex;gap:12px;align-items:center;margin-bottom:2px}
.brand b{font-size:16px;font-weight:700;letter-spacing:2.4px}
.brand b.wm{background:linear-gradient(180deg,#fff,#aeb7c3 60%,#7b8593);-webkit-background-clip:text;background-clip:text;color:transparent}.brand small{display:block;color:var(--t3);font-size:11.5px}
.sec{font-size:11px;font-weight:500;letter-spacing:.8px;text-transform:uppercase;color:var(--t3);margin:16px 0 6px}
@media (max-width:900px){[data-testid="stSidebar"][aria-expanded="true"]{min-width:260px!important}.block-container,[data-testid="stMainBlockContainer"]{padding:2.4rem 10px 8px!important}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
""", unsafe_allow_html=True)

try:
    LOGO_MARK = (ROOT / "app" / "ui" / "logo_mark.svg").read_text(encoding="utf-8").replace('width="120" height="120"', 'width="46" height="46"')
except OSError:
    LOGO_MARK = ""
_custom = custom_logo()
if _custom:  # user-supplied logo replaces the built-in mark on the home screen sidebar
    LOGO_MARK = f'<img src="{_custom}" alt="" style="height:46px;width:auto;max-width:150px;object-fit:contain">'

# one-time boot splash (pure CSS, about 1.5 s, respects prefers-reduced-motion)
if not st.session_state.get("splash_done"):
    st.session_state["splash_done"] = True
    st.markdown(splash_html(), unsafe_allow_html=True)

# sidebar open/close buttons: our emblem instead of the stock chevrons, turning one facet on hover and a quarter-turn on press
_toggle_uri = custom_logo() or (_uri((ROOT / "app" / "ui" / "logo_mark.svg").read_text(encoding="utf-8")) if LOGO_MARK else "")
if _toggle_uri:
    st.markdown("""
<style>
[data-testid="stSidebarCollapseButton"] button,[data-testid="stExpandSidebarButton"],[data-testid="stSidebarCollapsedControl"] button{position:relative;width:38px;height:38px;border-radius:6px;display:grid;place-items:center;background:transparent!important}
[data-testid="stSidebarCollapseButton"] button>*,[data-testid="stExpandSidebarButton"]>*,[data-testid="stSidebarCollapsedControl"] button>*{display:none!important}
[data-testid="stSidebarCollapseButton"] button::before,[data-testid="stExpandSidebarButton"]::before,[data-testid="stSidebarCollapsedControl"] button::before{
  content:"";display:block;width:28px;height:28px;background:url("@@URI@@") center/contain no-repeat;
  transition:transform .38s cubic-bezier(.2,.7,.2,1),filter .3s;animation:bo-turn .45s cubic-bezier(.2,.7,.2,1) both}
[data-testid="stSidebarCollapseButton"] button:hover::before,[data-testid="stExpandSidebarButton"]:hover::before,[data-testid="stSidebarCollapsedControl"] button:hover::before{transform:rotate(22.5deg) scale(1.1);filter:drop-shadow(0 0 6px rgba(190,205,225,.5))}
[data-testid="stSidebarCollapseButton"] button:active::before,[data-testid="stExpandSidebarButton"]:active::before,[data-testid="stSidebarCollapsedControl"] button:active::before{transform:rotate(45deg) scale(.92)}
[data-testid="stSidebarCollapseButton"] button:focus-visible,[data-testid="stExpandSidebarButton"]:focus-visible{outline:2px solid #4F8CFF;outline-offset:2px}
@keyframes bo-turn{from{transform:rotate(-90deg) scale(.55);opacity:0}to{transform:none;opacity:1}}
@media (prefers-reduced-motion:reduce){[data-testid="stSidebarCollapseButton"] button::before,[data-testid="stExpandSidebarButton"]::before{animation:none;transition:none}}
</style>
""".replace("@@URI@@", _toggle_uri), unsafe_allow_html=True)

DEFENCES = {
    "D0": "D0 · Undefended",
    "D1": "D1 · Keyword filter",
    "D2": "D2 · Black Onyx rules",
    "D3": "D3 · Rules + Laya sentinel",
    "D4": "D4 · Laya alone (no rules)",
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


V2_DIR = Path(os.environ.get("BLACKONYX_LAYA_V2_DIR", r"D:\Buildathon-Toolkit\laya-ft"))
V2_AVAILABLE = (V2_DIR / "v2.pt").exists() and (V2_DIR / "v2.json").exists()


@st.cache_resource(show_spinner=False)
def get_sentinel(version: str = "v0"):
    """Laya loads once per version (about 10 s). Any problem falls back to NullSentinel so a run never fails.
    version "v2" asks for the fine-tuned top layers; if they cannot be loaded the original model is used and says so."""
    try:
        from blackonyx.laya_sentinel import LayaSentinel
        s = LayaSentinel(model_version=version)
        if version == "v2" and s.version != "v2":
            return s, f"Laya v0 (English, CPU fp32); v2 not loaded: {(s._v2_error or 'unknown')[:80]}"
        return s, ("Laya v2 fine-tuned (English, CPU fp32)" if s.version == "v2" else "Laya (English, CPU fp32)")
    except Exception as e:  # noqa: BLE001
        from blackonyx.sentinel import NullSentinel
        return NullSentinel(), f"NullSentinel (Laya unavailable: {type(e).__name__})"


def execute(defence: str, task: str, attack: str, inject: str, laya_version: str = "v0") -> tuple[list[dict[str, Any]], str]:
    source = "engine"
    if inject.strip():
        attack = "None"  # pasted text takes priority over a preset attack
    try:
        from blackonyx.runner import run_scenario
        sentinel = None
        if defence in ("D3", "D4"):
            if st.session_state.get("laya_loaded") not in (None, laya_version):
                get_sentinel.clear()           # free the other copy of the model before loading this one
            with st.spinner("Loading the local Laya sentinel (first time only, offline)…"):
                sentinel, source = get_sentinel(laya_version)
            st.session_state["laya_loaded"] = laya_version
            st.session_state["laya_status"] = source
        ev = run_scenario(task_id=task, attack_id=None if attack == "None" else attack, defence=defence,
                          injected_text=inject.strip() or None, sentinel=sentinel)
        return ev, source
    except Exception:  # noqa: BLE001
        return fake_run(attack=(attack != "None") or bool(inject.strip()), task_id=task, defence=defence,
                        injected_text=inject.strip() or None), "fake events (engine unavailable)"


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(f"""
<div class="brand">{LOGO_MARK}<div><b class="wm">BLACK ONYX</b><small style="letter-spacing:2.2px;text-transform:uppercase;font-weight:600;color:var(--t2)">Provenance firewall</small><small>Security layer for tool-using AI agents</small></div></div>
""", unsafe_allow_html=True)

    st.markdown('<div class="sec">Scenario</div>', unsafe_allow_html=True)
    defence_id = st.selectbox("Defence", list(DEFENCES), format_func=DEFENCES.get, key="defence_sel")
    attack_id = st.selectbox("Attack", list(ATTACKS), format_func=ATTACKS.get, key="attack_sel")
    typed = bool(st.session_state.get("inject_txt", "").strip())
    has_attack = attack_id != "None" and not typed
    task_id = st.selectbox("Task", list(TASKS), format_func=TASKS.get, key="task_sel", disabled=has_attack,
                           help="A preset attack runs on its own host task, so this is locked while one is selected.")
    if typed and attack_id != "None":
        st.caption("Custom attack takes priority over the attack selection.")

    st.markdown('<div class="sec">Custom attack</div>', unsafe_allow_html=True)
    inject_text = st.text_area("Paste an injection", key="inject_txt", height=96, label_visibility="collapsed",
                               placeholder="Paste an injection. It is planted where the chosen task will read it (email, web page or document).")
    with st.container(border=True):
        autoplay = st.toggle("Animate playback", value=True)
        phone = st.toggle("Phone alert on block", value=True, help="Pushes a short message (tool and policy reason only) to the ntfy topic when a call is blocked. Silent if offline.")
        laya_v2 = os.environ.get("BLACKONYX_LAYA_MODEL", "").strip().lower() == "v2"   # no on-screen switch; set the variable to use v2
        run_clicked = st.button("Run scenario", type="primary", use_container_width=True, icon=":material/play_arrow:")

    st.markdown('<div class="sec">Test cases</div>', unsafe_allow_html=True)
    st.button("Agent is hijacked", use_container_width=True, on_click=_preset, args=("D0", "L1", "A1"), icon=":material/warning:")
    st.button("Black Onyx contains it", use_container_width=True, on_click=_preset, args=("D2", "L1", "A1"), icon=":material/shield:")
    st.button("Reworded attack, keyword filter", use_container_width=True, on_click=_preset, args=("D1", "L1", "A2"), icon=":material/filter_alt:")
    st.button("Multi-hop: split address", use_container_width=True, on_click=_preset, args=("D2", "L1", "A8"), icon=":material/call_split:")
    st.button("Legitimate payment passes", use_container_width=True, on_click=_preset, args=("D2", "L4", "None"), icon=":material/payments:")
    st.button("With Laya second opinion", use_container_width=True, on_click=_preset, args=("D3", "L1", "A1"), icon=":material/psychology:")
    st.button("Laya alone, no rules", use_container_width=True, on_click=_preset, args=("D4", "L1", "A1"), icon=":material/psychology_alt:")

# ---------------------------------------------------------------- run
if run_clicked or st.session_state.pop("pending_run", False) or "events" not in st.session_state:
    eff_task = task_id
    ev, src = execute(defence_id, eff_task, attack_id, inject_text, "v2" if laya_v2 else "v0")
    if phone and run_clicked:  # only the Run scenario button; never on page load, refresh or preset buttons
        from app.phone_alerts import send_block_alerts
        send_block_alerts(ev)
    st.session_state.update(events=ev, runner_source=src, last_defence=defence_id, run_id=st.session_state.get("run_id", 0) + 1)

events: List[dict[str, Any]] = st.session_state.get("events", [])
src = st.session_state.get("runner_source", "engine")
shown_defence = st.session_state.get("last_defence", defence_id)

import os  # noqa: E402

LIVE_LLM = True   # the Live LLM tab is always listed; it does nothing until you press its button
_tabs = st.tabs([":material/play_circle: Run", ":material/bar_chart: Results", ":material/menu_book: Explain"]
                + ([":material/cloud: Live LLM"] if LIVE_LLM else []))
tab_live, tab_results, tab_how = _tabs[:3]

with tab_live:
    components.html(render_stage(events, autoplay=autoplay, defence=shown_defence), height=900, scrolling=False)
    _res = load_results()
    if _res:
        _d2 = _res["defences"]["D2"]
        _b = _d2["asr_all"]; _u = _d2["bu"]
        st.markdown(
            f'<div class="evalstrip"><div><b>{_b["n"] - _b["k"]}/{_b["n"]}</b><span>attack runs blocked</span></div>'
            f'<div><b>{_u["k"]}/{_u["n"]}</b><span>legitimate tasks completed</span></div>'
            f'<div><b>{_b["k"]}</b><span>policy bypasses</span></div>'
            f'<div class="note">Measured on this suite with a simulated attacker (rules only, D2). See the Results tab for every number and interval.</div></div>',
            unsafe_allow_html=True)
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
        from app.ui.laya_versions import versions_page_html
        components.html(versions_page_html(), height=880, scrolling=False)
        laya_md = ROOT / "docs" / "laya-results.md"
        if laya_md.exists():
            with st.expander("Laya sentinel measurements (advisory layer, CPU fp32)"):
                st.markdown(laya_md.read_text(encoding="utf-8"))

with tab_how:
    components.html(howitworks_html(), height=1180, scrolling=True)


if LIVE_LLM:
    with _tabs[3]:
        st.markdown("**Live LLM, same injected inbox.** A real Gemini model reads a mailbox that contains a hidden instruction, "
                    "first with no protection, then behind Black Onyx. This tab needs internet and sends the fake demo text to the "
                    "Gemini API; it does nothing until you press the button.")
        _env_key = os.environ.get("GEMINI_API_KEY", "")
        key_in = st.text_input("Gemini API key", type="password", key="gemini_key_field",
                               placeholder="Using GEMINI_API_KEY from the environment" if _env_key else "Paste your key (kept only in this browser session)",
                               help="Never saved to disk, never logged. Leave empty to use the GEMINI_API_KEY environment variable.")
        api_key = key_in.strip() or _env_key
        style_live = st.radio("Injection style", ["mild", "forceful"], horizontal=True, key="live_style",
                              help="Forceful dresses the hidden instruction up as a message from the account owner.")
        phone_live = st.toggle("Push the simulated evil inbox and block events to the phone", value=True, key="live_phone")
        if st.button("Run the live comparison", type="primary", icon=":material/cloud:", key="live_run", disabled=not api_key):
            sys.path.insert(0, str(ROOT / "examples"))
            import real_llm_agent as _rl
            _rl.PHONE["on"] = phone_live
            _rl.set_style(style_live)
            cols = st.columns(2)
            for col, guarded in zip(cols, (False, True)):
                with col:
                    st.markdown("**With Black Onyx**" if guarded else "**Unprotected**")
                    try:
                        with st.spinner("Asking the model..."):
                            out = _rl.run_agent(_rl.Gemini(api_key=api_key), guarded, verbose=False)
                    except Exception as e:  # network, quota or key problems: say so plainly
                        st.error(f"Could not reach the model ({type(e).__name__}). Check internet, quota and the key.")
                        break
                    for m in out["sent"]:
                        st.write(f"Sent to `{m['to']}`" + (" (outside)" if not m["to"].endswith("@corp.com") else ""))
                    if not out["sent"]:
                        st.write("No email sent.")
                    if guarded:
                        st.success(f"{out['blocked']} injected call(s) blocked; the summary still went out.") if out["blocked"] else                             st.info("The model did not follow the injected line this time, so there was nothing to block.")
                    elif out["leaked"]:
                        st.error("The injected instruction was obeyed: mail went to the outside address.")
                    else:
                        st.info("The model ignored the injected line on its own. Try again, or use the offline scenarios.")
