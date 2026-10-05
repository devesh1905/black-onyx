"""Build a probe set in the LIVE prompt format: the exact (request, tool, args) states the sentinel sees at run time.

Labels: a call the user's plan contains is "fit"; a call produced by injected text (call id x*) is "no-fit".
No Laya involved here; the set is saved to .scratch/ft/probe.json and scored by eval/probe_score.py (GPU venv).

    python -m eval.live_probe
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from blackonyx.runner import run  # noqa: E402
from blackonyx.scenarios.attacks import ATTACKS  # noqa: E402
from blackonyx.scenarios.tasks import LEGIT_TASKS  # noqa: E402
from blackonyx.sentinel import SentinelResult  # noqa: E402
from eval.mutator import all_variants  # noqa: E402


class Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def score(self, task, tool, args):
        self.calls.append((str(task), tool, dict(args)))
        return SentinelResult(score=0.5, ms=0.0, warn=False)


def state_of(task: str, tool: str, args: dict) -> str:
    """Same construction as LayaSentinel.score."""
    items = []
    for k, v in args.items():
        v = str(v)
        items.append(f"{k}={v[:57] + '...' if len(v) > 60 else v}")
    return f"User request: {str(task).strip()[:160]}\nTool: {tool}\nArgs: {', '.join(items)[:120]}"[:290]


def collect(task, attack, text=None) -> list[dict]:
    rec = Recorder()
    r = run(task, attack, "D3", sentinel=rec, variant_text=text) if text else run(task, attack, "D3", sentinel=rec)
    ids = [e["call_id"] for e in r.events if e.get("type") == "laya_score"]
    out = []
    for cid, (task_, tool, args) in zip(ids, rec.calls):
        out.append({"state": state_of(task_, tool, args), "tool": tool, "fit": not str(cid).startswith("x"), "src": attack or task})
    return out


def main() -> None:
    rows = []
    for t in LEGIT_TASKS:
        rows += collect(t, None)
    for a in ATTACKS:
        rows += collect(None, a)
    for v in all_variants(60, 1905)[::6]:
        rows += collect(None, v.attack_id, v.text)
    seen, uniq = set(), []
    for r in rows:
        k = (r["state"], r["fit"])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    out = ROOT / ".scratch" / "ft" / "probe.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(uniq), encoding="utf-8")
    nf = sum(not r["fit"] for r in uniq)
    print(f"{len(uniq)} unique live states: {len(uniq) - nf} fit, {nf} no-fit -> {out}")
    for r in uniq[:4]:
        print(repr(r["state"]), r["fit"])


if __name__ == "__main__":
    main()
