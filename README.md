# Black Onyx

A provenance firewall for tool-using AI agents, plus a local sentinel model (Laya).
Team Cyberix, VELS Buildathon 2026, problem AG03 "The Agent That Survives a Poisoned Tool".

Untrusted tool output may be **read and used as data**, but it can never choose a **destination or action**.
Every value carries `{sources, trust}`; every tool call is checked against a readable YAML policy.
See `docs/trust-model.md`, `docs/event-schema.md`, `docs/results.md`.

## Run (offline, CPU)
```
python -m venv .venv
.venv\Scripts\activate
pip install --no-index --find-links D:\Buildathon-Toolkit\wheels-black-onyx -r requirements.txt
pytest -q
python -m eval.run_eval --check-repro        # all tables -> docs/results.md
streamlit run app/streamlit_app.py           # split-screen demo with live provenance graph
python demo/replay.py runs/example.jsonl     # terminal fallback
```
Laya numbers: CPU, fp32, English checkpoint only (see `docs/laya-results.md`).

## Layout
`src/blackonyx/` engine (labels, labeled, interpreter, policy, validators, planner, world, scenarios) ·
`policy/policy.yaml` · `eval/` mutator + harness · `app/` UI · `demo/` replay · `tests/`

## Defences compared
D0 undefended · D1 keyword filter · D2 Black Onyx rules · D3 rules + Laya (advisory) · D4 Laya alone (ablation).

## Honest limits
The attacker-following agent is a simulation of a compliant LLM. Results hold for this suite (8 legit tasks,
10 attacks, 300 generated variants), not as a claim of unbreakability. Laya is advisory; rules do the blocking.
