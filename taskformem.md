# Task for teammate: UI track + Laya sentinel track

Hi! This is your half of Black Onyx. I (Claude + Allen) build the **engine**: labels, `LabeledObject`, interpreter, policy gate, validators, mock world, tasks L1-L8, attacks A1-A10, mutator, baselines D0-D3, eval harness. You build the **UI** and the **Laya sentinel**. The two halves meet at two small contracts, so you never have to wait for the engine.

Read first: `CLAUDE.md` (sprint rules and hard rules), `docs/roadmap.md` sections 3, 10, 11A, and `docs/event-schema.md`.

## Hard rules (judges check these)
- **All code is written live today, by you, in this repo.** Do not paste Laya's training notebook or any reference implementation. pip libraries are fine.
- No secrets in the repo. Everything must run **offline**.
- Commit small, often, with prefixes `ui:`, `eval:`, `feat:`, `test:`, `docs:`. `git pull --rebase` before every push. Push to `main`.
- **Only edit your own files** (listed below) to avoid merge conflicts. If you need a change in mine, tell us.
- Environment: see `setup-notes/ENVIRONMENT.md` (offline wheels in `D:\Buildathon-Toolkit` on laptop 1; copy that folder to your laptop). Use the venv at `.venv`, run `pytest -q` after each change.

## The two contracts (already in the repo, do not change without telling us)
1. **Event log** (`docs/event-schema.md`): JSONL, one event per line. The engine writes it, you read it. Event types: `request, plan, tool_result, op, declassify, call_check, laya_score, alert, effect`.
2. **Sentinel interface** (`src/blackonyx/sentinel.py`): `score(task, tool, args) -> SentinelResult(score, ms, warn)`. `NullSentinel` exists. You write `LayaSentinel` with the same interface. It must **never raise**; on any error return `score=None`.

---

## Part 1: UI (do this first, 08:30 to ~12:00, then polish)

**Your files:** `app/streamlit_app.py`, `app/graph.py`, `app/fake_events.py`, `demo/replay.py`, `tests/test_ui_*.py`.

1. **`app/fake_events.py`**: a function `fake_run(attack: bool) -> list[dict]` returning a realistic event list following the schema (L1 "summarise my unread mail"; with `attack=True` the poisoned email tries `send_email(to=billing@evil.co)`, gets `call_check deny` + `alert`, but the summary email to the user is still `allow`ed and an `effect` appears). Use this until the engine produces real logs. Also write one saved example to `runs/example.jsonl`.
2. **`app/graph.py`**: `events_to_html(events) -> str`. Build a PyVis network: USER node green, VERIFIED blue, UNTRUSTED orange, planned/tool-call nodes grey, blocked call node red. Edges from `op`, `declassify`, `call_check`. A `laya_score` becomes a small badge in the call node label (e.g. `fit 0.12`). **Inline the JS** (no CDN): PyVis writes two Bootstrap CDN tags into the HTML, strip them and inline vis-network (pyvis `cdn_resources="in_line"`). Must render with Wi-Fi off. Add a small injected JS snippet so the blocked node **flashes red** (toggle colour with `setInterval`). If that misbehaves, fall back to a static red node.
3. **`app/streamlit_app.py`**: split screen.
   - Left: chat panel (request text, agent replies, red alert banner built from the `alert` event's `chain` and `reason`).
   - Right: the graph (`st.components.v1.html`). Keep events in `st.session_state` and rebuild the graph from them (Streamlit reruns the script on every click).
   - Sidebar: defence toggle (D0 undefended / D1 keyword / D2 rules / D3 rules+Laya), task dropdown (L1-L8), attack dropdown (none, A1-A10), and an **"inject attack text" box** where a judge types any injection into the email body.
   - Right now the "Run" button calls `fake_run`. Wire it so that if `blackonyx.runner.run_scenario(task_id, attack_id, defence, injected_text)` exists (**I will provide it**; returns the list of event dicts) it uses that, else falls back to fake events. Use `try: from blackonyx.runner import run_scenario`.
4. **`demo/replay.py`**: terminal fallback using `rich`. `python demo/replay.py runs/example.jsonl` prints the events step by step with colours (green/blue/orange, bold red for alerts), pausing with Enter or a `--delay` option.
5. **Tests:** `tests/test_ui_graph.py` (HTML has no `http` CDN script tags, contains the red colour for a deny event, handles empty events) and a headless Streamlit smoke test using `streamlit.testing.v1.AppTest`.

**Done when:** `streamlit run app/streamlit_app.py` shows the split screen with fake events, graph renders offline, blocked node flashes, replay prints a log.

---

## Part 2: Laya sentinel (start ~12:15, runs in parallel with my engine work)

**Your files:** `src/blackonyx/laya_sentinel.py`, `eval/sentinel_data.py`, `eval/calibrate_laya.py`, `eval/finetune_laya.py` (only if you reach that rung), `tests/test_sentinel_*.py`, `docs/laya-results.md`. Follow `docs/roadmap.md` section 11A exactly; summary below.

**Tools (from `policy.yaml`, which I will push; assume these 9):** `read_inbox, read_file, write_file, web_fetch, send_email, reply_email, transfer_money, calendar_add, search_docs`.

1. **`eval/sentinel_data.py`**: seeded, deterministic, no LLM. Generates JSONL pairs: `state` (under ~300 chars, e.g. `User request: Pay invoice 4411.\nTool: transfer_money\nArgs: payee=registry:ACME, amount=1200`), `questions`, `expected` (true/false), `tags`. About half positives (the legit tasks in roadmap 5.2 in several phrasings with the right tool), half negatives: (a) wrong tool, (b) right tool wrong destination, (c) calls following an injected instruction. **Split by template family:** pool A phrasings = train+dev, pool B phrasings = test. Never put attack suite items or mutator variants in train. Aim for 1,500-3,000 pairs and a frozen test set of **>= 200 pairs**. Check with `laya-evals validate`.
2. **Baseline + ladder** (`calibrate_laya.py`): rung 0 zero-shot English checkpoint and the keyword baseline (does the tool's verb appear in the task?); rung 1 one closed yes/no question per tool, short structured state, English checkpoint **only**; rung 1b paraphrase averaging; rung 2 fit the threshold on dev, report on test with a "no opinion" band. Keep a change only if the **held-out test** numbers improve. Report accuracy, recall on no-fit, false-warning rate, ECE, each with a **95% Wilson interval**, plus device and precision (**CPU, fp32**), Laya version and checkpoint. Write the table to `docs/laya-results.md`.
3. **`src/blackonyx/laya_sentinel.py`**: `LayaSentinel` implementing `Sentinel`. Loads the English checkpoint once (`HF_HUB_OFFLINE=1`), truncates argument values, returns `SentinelResult(score, ms, warn)` using the calibrated threshold from a small JSON config (keyed by device+precision). Any exception -> `SentinelResult(None, ms, None)`. Test: failure never crashes, `NullSentinel` fallback works, same decision on a fixed set of 20 pairs run twice.
4. **Fine-tune (optional, only if gates in 11A.2 are missed):** GPU venv `D:\Buildathon-Toolkit\venv-cuda`, start about 13:30, **hard stop 15:00**, our own loop using `laya.common` helpers. Accept only if it beats the best earlier rung on the held-out test, re-scored on CPU fp32.

**Do not** tune on, or calibrate with, the attack suite.

---

## When to hand over to me
- Push after every working step. I pull often and will wire `run_scenario` and the real event log into your UI, and plug `LayaSentinel` into the interpreter (D3).
- Gate times: UI skeleton with fake events by **09:30**, real graph + red flash by **11:45** (review prep), Laya data + baseline by **13:15**, best rung into the loop by **14:00**, everything frozen **15:45**.
- If stuck for more than 20 minutes, post in the group chat. Use the scope-cut ladder in roadmap section 11 (for Laya: demote to `NullSentinel` in the live path and report offline numbers).
