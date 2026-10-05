# CLAUDE.md: BUILD SPRINT MODE (Black Onyx, VELS Buildathon, AG03)

**This is a build sprint. Work as fast as you can and start building immediately.**
It is build day (Mon 5 Oct 2026). The first commit is allowed (it is after 08:00). The Progress Review is at 12:00 and the Final Review at 16:30, so every hour counts. The full plan is in `roadmap.md` (copy it into the repo as `docs/roadmap.md` on the first commit, or read it from `D:\Downloads\Buildathon Vels\roadmap.md`).

## How to behave (speed first)
- **Do not ask permission for routine choices.** Pick a sensible default, say it in one line, keep going. Ask the user only when blocked by something only they can decide (visibility of the repo, an API key, who does what).
- **Do the next milestone, not a plan for it.** Write the code, run the tests, commit, push. Short status lines only ("G0 done, starting labels").
- **Small, working steps.** Commit and push at least every 20-30 minutes. Run `pytest -q` after every change. Never leave `main` broken.
- **Work in parallel when parts are independent** (for example the mock world and the Streamlit skeleton): use subagents or separate files, and merge often.
- **Protect the core first** (labels, propagation, policy gate, validators, L1-L5, A1-A8, harness, graph with red flash). Polish only after G3 (15:00). If a task runs over its time box, cut scope using roadmap section 11.
- **Keep it deterministic:** seeded randomness, no network at runtime, same output every run.

## Hard rules (do not break these)
1. **All code is written live, in this repo, from now on.** Do not paste or adapt reference implementations (CaMeL, FIDES, AgentDojo) or Laya's training notebook. Libraries from pip are fine. Cite papers as inspiration only.
2. **No secrets in the repo.** API keys go in a local `.env` outside the repo. The core system needs no key.
3. **Everything must run offline** on a fresh clone in under 5 minutes (clean-clone test at 16:15).
4. **Laya is an advisor.** It warns and never overrides a rule. English checkpoint only in the live path. Rules do the blocking.
5. **Report only measured numbers**, with counts and 95% intervals. No "100+ languages", no "33 ms".

## First 10 minutes (do these now, in order)
1. Read `roadmap.md` sections 2, 3 (trust model, architecture, event schema, policy), 5 (tasks and attacks), 6 (metrics) and 10 (repo layout).
2. Create the repo (the GitHub repo `black-onyx` did not exist at 08:36; the roadmap says public or shared with judges):
   ```
   cd D:\
   gh repo create black-onyx --public --clone
   cd black-onyx
   ```
3. Set up the environment (offline, from the toolkit, see `ENVIRONMENT.md`):
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install --no-index --find-links D:\Buildathon-Toolkit\wheels-black-onyx -r D:\Buildathon-Toolkit\req-black-onyx.txt
   ```
4. Create the layout from roadmap section 10, add a README skeleton, write the event schema and function signatures, **make the first commit and push.**
5. Start the milestones below.

## Milestones (times from the roadmap)
| Gate | Time | What must exist |
|---|---|---|
| G0 | 09:30 | Mock world, tasks L1-L5, undefended agent D0, effect recorder |
| G1 | 10:30 | Labels and propagation, policy gate, A1 blocked, property tests |
| Review prep | 11:45 | Tag `review-1200`; graph shows a real L1 run and the A1 block |
| **Progress Review** | **12:00** | Share the repo. Show D0 hijacked, then Black Onyx blocking A1 |
| G2b | 14:00 | Validators done; Laya in the loop (best rung so far) or `NullSentinel` |
| G3 (MVP) | 15:00 | Attacks, mutator, metrics tables. **Laya fine-tune hard stop.** |
| Feature freeze | 15:45 | Tag `review-1630`; then package, README, results from real output |
| G5 | 16:15 | Clean clone on another laptop, Wi-Fi off, demo runs |
| **Final Review** | **16:30-18:00** | Present, demo, Q&A |

## Laya sentinel (accuracy first; see roadmap section 11A)
- Freeze the **held-out test set before** tuning anything. Never train or calibrate on the attack suite you report.
- Climb the ladder: baseline, closed per-tool questions, paraphrase averaging, calibrate the **threshold** (the 0.5 default produced false warnings; ranking was perfect on our smoke test), then fine-tune only if needed (GPU venv, start about 13:30, stop 15:00).
- Score on **CPU, fp32**. If a GPU is used, set `LAYA_CUDA_AMP=fp16` and fit the threshold in that same setting.
- Beat the keyword baseline or say so. Report device, precision, Laya version and checkpoint next to every number.

## Tools on this laptop
- Python 3.13, git, gh (logged in as `devesh1905`), VS Code, Antigravity, Claude Code.
- Packages and models are pre-installed and offline: see `ENVIRONMENT.md` (`HF_HOME` is already set for the user).
- Free disk: **C: is nearly full. Build on D:. Never put the repo, venvs or caches on C:.**
