# Black Onyx

A provenance firewall for tool-using AI agents, with a small local advisory model (Laya).
Team Cyberix, VELS Buildathon 2026, problem AG03 "The Agent That Survives a Poisoned Tool".

Untrusted tool output (email, web page, file, search result) can be **read and used as data**, but it can never
**choose a destination or an action**. Every value carries `{sources, trust}`, the labels survive every operation,
and a readable YAML policy checks each tool argument at the moment of use. The decision depends on where a value
came from, not on what the text says, so rewording an attack does not change the outcome.

Docs: **[benchmarks page](docs/judge-prompts/index.html)** (open in a browser; also has the judge prompts) · [trust model](docs/trust-model.md) · [event schema](docs/event-schema.md) · [results](docs/results.md) ·
[Laya measurements](docs/laya-results.md) · [Laya extras](docs/laya-extra.md) · [Laya fine-tune](docs/laya-finetune.md) · [red-team pass](docs/redteam.md) · [judge prompts](docs/judge-prompts.md) · [simple notes (PDF)](docs/notes/Black-Onyx-Simple-Notes.pdf)

## Requirements

- Windows, Python 3.11+ (developed on 3.13), no GPU needed, **no network at run time**.
- For the Laya sentinel: the English checkpoint in a local Hugging Face cache (see "Offline toolkit" below).
  Everything else works without it: if Laya cannot load, the app shows "no opinion" for it and the rules still decide.

## Install (offline)

The pinned packages are available as wheels in the team toolkit folder `D:\Buildathon-Toolkit` (copy that folder to
any laptop you want to run on).

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install --no-index --find-links D:\Buildathon-Toolkit\wheels-black-onyx -r requirements.txt
```

With internet instead, `pip install -r requirements.txt` works too.

### Offline toolkit (models)

Laya's English checkpoint lives in `D:\Buildathon-Toolkit\hf-cache`. The sentinel looks there first, then in
`%HF_HOME%\hub`. On another machine, copy the toolkit folder and set the cache once:

```powershell
setx HF_HOME "D:\Buildathon-Toolkit\hf-cache"      # open a new terminal afterwards
set HF_HUB_OFFLINE=1                               # the sentinel also sets this itself
```

## Run

```powershell
pytest -q                                   # all tests (137; about 30 s; the sentinel tests load Laya)
python -m eval.run_eval --check-repro       # rules-only tables -> docs/results.md and docs/results.json
python -m eval.run_eval --laya-all          # D3/D4 with the real sentinel on all 300 variants (about 10 min on CPU)
python -m eval.redteam                      # hand-written injection battery under D2
python scripts/build_prompts_html.py        # rebuild docs/judge-prompts/index.html (benchmarks + judge prompts)
python -m eval.laya_ladder                  # Laya measurements on the full held-out set -> docs/laya-results.md
streamlit run app/streamlit_app.py          # the demo UI (http://localhost:8501)
python demo/replay.py runs/example.jsonl    # terminal fallback replay
```

Do not run the demo UI and the full test suite at the same time with Laya loaded in both: each copy of the model
needs about 2 GB of RAM.

## The demo UI

- **Run** tab: pick a defence (D0 undefended, D1 keyword filter, D2 Black Onyx rules, D3 rules + Laya), an attack and a
  task, then Run. Or press one of the six demo scenarios. The result block, the decision table, the event timeline and the
  provenance graph all come from the engine's event log. The graph can be expanded to the full window, and its boxes can be
  dragged.
- **Custom attack**: paste any injection text. It is planted where the chosen task will read it (email, web page or
  document). `docs/judge-prompts.md` has 14 ready-made prompts, also listed inside the app.
- **Results** and **Explain** tabs: the measured tables and a one-page explanation of the trust model.
- Laya appears as a **Fit %** (how well a call matches the request). It is advisory and never blocks.

### Optional branding

Drop your own images in `app/ui/brand/` (`emblem.png` for the splash, `logo.png` for the home-screen logo), or set
`BLACKONYX_EMBLEM` / `BLACKONYX_LOGO`. `BLACKONYX_SPLASH_SCALE` (default 1.8) stretches or shortens the boot splash.
See `app/ui/brand/README.md`. These files are git-ignored.

## Layout

```
policy/policy.yaml           the readable policy (per tool, per argument)
src/blackonyx/               labels, labeled values, planner, interpreter, policy gate, validators,
                             sentinel (Laya), audit log, mock world, scenarios (tasks L1-L9, attacks A1-A10)
eval/                        attack mutator, harness, Laya data and calibration ladder
app/                         Streamlit shell and the self-contained stage (HTML/SVG/CSS/JS, no CDN)
demo/replay.py               terminal replay of a saved log
tests/                       unit, property, scenario, metamorphic, mutation-check, UI and judge-prompt tests
docs/                        trust model, event schema, results, wireframes, notes
```

## Measured results (simulated attacker, this suite only)

8 legitimate tasks, 10 attacks and 300 generated reworded variants, seed 1905 (`docs/results.md`):

| Defence | Attack runs that got through | User's task still finished |
|---|---|---|
| D0 undefended | 310 / 310 | 80.0% |
| D1 keyword filter | 281 / 310 | 80.0% |
| D2 Black Onyx rules | 0 / 310 (95% upper bound 1.2%) | 99.7% |
| D3 rules + Laya (advisory) | 0 / 310 | 99.7% |
| D4 Laya alone (no rules) | 2 / 310 | 25.2% |

All 8 legitimate tasks still finish under D2, with 0 legitimate calls wrongly blocked and 0 false alerts. The policy
decision is identical for all 300 variants. The rule check takes about 10 microseconds per tool call; Laya takes about
0.3 s per call on CPU and never delays or overrides a rule decision. D3 and D4 ran on all 300 variants. Laya alone (D4)
lets 2 attacks through and finishes the user's task in only 25% of attack runs, which is why the rules do the blocking.
A hand-written red-team pass (153 runs, plus direct attacks on the policy and guard) found and fixed one real bypass in
the guard adapter and let 0 attacks through under D2 (`docs/redteam.md`).

### Laya versions (same held-out set of 400 call-fit pairs; thresholds fitted on dev only)

| Version | Accuracy | Recall on bad calls | False warnings | Latency (CPU / GPU) | In the demo |
|---|---|---|---|---|---|
| v0 original checkpoint | 81.0% | 77.0% | 15.0% | 288 ms / 32 ms | yes |
| v1 top 4 layers, 3 epochs | 90.5% | 96.0% | 15.0% | 288 ms / 32 ms | no |
| v2 top 8 layers (mean of 5 seeds) | 90.9% | 98.6% | 16.7% | 288 ms / 32 ms | opt-in switch |
| v2 + keyword stack (mean of 3 seeds) | 92.9% | 98.5% | 12.7% | 288 ms / 32 ms | no |
| v3 five-seed unanimous vote of v2 | 95.2% | 98.0% | 7.5% | 1,146 ms / 161 ms | no |

The keyword baseline scores 75.8% / 70.5% / 19.0% on the same set. On 45 real runtime states (a small format check) v0 has
31.0% false warnings and catches 68.8% of injected calls; v3 has 17.2% and 93.8%, because the training data has no
empty-argument or runtime-style calls yet. The fine-tuned weights are not in the repository. v2 can be switched on in the sidebar when its weights are present (D3 and D4, off by default); the demo runs v0.
Details: `docs/laya-finetune.md`, `docs/laya-extra.md`, `docs/laya-results.md`.

## Honest limits

- The attacker-following agent is a simulation of a compliant model, not a real LLM. The results show the mechanism works
  on this suite; they are not a claim that a real agent is unbreakable.
- A poisoned page can still make a summary's wording misleading (summaries stay labelled untrusted). Implicit flows
  (branching on tainted data) are out of scope.
- The guard adapter recovers provenance by matching text against the request and tool output; a red-team pass fixed one
  real bypass there (`docs/redteam.md`). An allow-listed URL host can still receive data in the URL path, so allow-list
  only hosts you control.
- Laya is a second opinion only. The live checkpoint (v0) does not meet the accuracy gates we set (`docs/laya-results.md`); the
  fine-tuned versions meet the accuracy and recall gates on the held-out set but are not yet validated on live-format calls and
  are not wired into the demo (`docs/laya-finetune.md`).
