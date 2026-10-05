# UI/UX brief for the Black Onyx demo

Open `index.html` in a browser to see the wireframes (7 screens). This file is the spec that goes with them.

## What already exists
A first Streamlit UI is in `app/` (`streamlit_app.py`, `graph.py`, `fake_events.py`) and `demo/replay.py`.
It already runs the real engine (`blackonyx.runner.run_scenario`) and draws the PyVis graph offline.
Your job is to take it from "works" to "demo-quality", following these wireframes.

## Files you own
`app/**`, `demo/replay.py`, `docs/wireframes/**`, `tests/test_ui_*.py`. Do not edit `src/blackonyx/**` (tell the engine owner instead).

## Data contract
Read only the event list (JSONL) described in `docs/event-schema.md`. `run_scenario(task_id, attack_id, defence, injected_text)` returns it.
Event types: `request, plan, tool_result, op, declassify, call_check, laya_score, alert, effect`.
Colours: green USER, blue VERIFIED, orange UNTRUSTED, red flash BLOCKED, purple Laya badge, grey planned call.

## Screens and what to build
| # | Screen | Must have | Nice to have |
|---|---|---|---|
| 1 | Main split screen, D0 hijacked | 3 columns (controls, chat, graph), defence segmented toggle, task + attack dropdowns, injection box, Run button, "hijacked" banner, world-effects line | per-run status chip |
| 2 | Black Onyx blocks it | red flashing node, red banner with provenance chain and reason, green "summary delivered", Laya "second opinion" line, scoreboard (task done, leaks, alerts, rule time) | animation that draws edges in event order |
| 3 | Node details drawer | click a node or alert: value, trust, sources, policy rule, argument kind (control/data), Laya fit, vertical provenance timeline | copy-chain button |
| 4 | Legit work passes | L4 run shows blue validator nodes (`declassify` events) with the rule on hover | rejected validator (`ok:false`) shown grey with a tag |
| 5 | Results dashboard | cards (ASR D0/D1/D2, BU, overblocking), per-attack table, latency, always-visible honest-limits box; every number with count and 95% interval | click a row to replay that attack |
| 6 | Laya panel + replay bar | score per call with threshold line; replay slider rebuilding the graph from the first N events | load any `runs/*.jsonl` |
| 7 | Narrow layout | stacked columns, pinned alert banner | |

## Behaviour details
- **Flash:** on an `alert` event, the node of that `call_id` flashes red (CSS animation, repeat until next run) and the banner slides into chat. Fallback: static red node + banner.
- **Graph build:** rebuild from `st.session_state` events on every rerun (Streamlit reruns the whole script). Node per `value_id` and per `call_id`; edges from `op.inputs -> op.output`, `declassify.input -> output`, `call_check.value_id -> call node`.
- **Declassify with `ok:false`:** the validator rejected the input, so no blue node; show a grey node tagged "rejected".
- **Out-of-plan calls** have ids `x1, x2...`; draw them as call nodes outside the planned chain (they are the ones that get blocked).
- **Attack runs choose their own host task** (see `docs/event-schema.md`), so grey out the task dropdown when an attack is selected.
- **Live injection box:** text typed by a judge becomes a new unread email; show a small "email #N from unknown@outside.example" node.
- **Offline:** inline all JS/CSS; PyVis must use inlined resources, no CDN tags. Test with Wi-Fi off.
- **Readability:** dark theme, body text >= 16 px on the projector, node labels >= 14 px, never colour alone (add the word BLOCKED and a ⛔ icon).

## Acceptance checklist
- [ ] `streamlit run app/streamlit_app.py` shows Screen 1 and Screen 2 for A1 with D0 vs D3 using the real engine
- [ ] Graph renders with Wi-Fi off, blocked node flashes
- [ ] Judge can type an injection and see it turn red while the task finishes
- [ ] L4 shows blue validator nodes; no false alert on any clean L1-L8 run
- [ ] Results screen numbers come from the harness output (`docs/results.md` or its JSON), never typed by hand
- [ ] `pytest -q tests/test_ui_*.py` passes; `python demo/replay.py runs/example.jsonl` works as the terminal fallback
- [ ] Commit small, prefix `ui:`, `git pull --rebase` before push
