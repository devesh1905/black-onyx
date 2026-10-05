"""Seed-vote analysis for the fine-tuned Laya: warn only if at least k of N seeds warn. Thresholds are per-seed, fitted on DEV.

    python -m eval.vote_analysis          # reads .scratch/ft/final_seed*.json (eval/finetune_seeds.py)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from eval.ft_analysis import acc_threshold, logit, sigmoid  # noqa: E402

FT = ROOT / ".scratch" / "ft"


def rates(warn, y):
    fit, nofit = y == 1, y == 0
    return {"acc": float(((~warn) == fit).mean()), "recall": float(warn[nofit].mean()), "fw": float(warn[fit].mean()),
            "n_fit": int(fit.sum()), "fw_n": int(warn[fit].sum()), "n_bad": int(nofit.sum()), "rec_n": int(warn[nofit].sum())}


def fmt(name, r):
    return f"{name:34s} acc {r['acc']:.1%} | recall {r['recall']:.1%} ({r['rec_n']}/{r['n_bad']}) | false warnings {r['fw']:.1%} ({r['fw_n']}/{r['n_fit']})"


def main() -> None:
    runs = sorted((json.loads(f.read_text(encoding="utf-8")) for f in FT.glob("final_seed*.json")), key=lambda r: r["seed"])
    runs = [r for r in runs if "probe_p" in r]
    n = len(runs)
    print(f"{n} seeds: {[r['seed'] for r in runs]}  (8 layers, lr 5e-5)")
    yd, yt, yp = (np.array(runs[0][k]) for k in ("dev_y", "test_y", "probe_y"))
    thr = [acc_threshold(np.array(r["dev_p"]), yd) for r in runs]
    print("per-seed dev thresholds:", [round(t, 3) for t in thr])
    PT = np.array([r["test_p"] for r in runs])
    PP = np.array([r["probe_p"] for r in runs])
    PN = np.array([r["probe_p_none"] for r in runs])
    out = {}
    for label, P, y in (("TEST (400)", PT, yt), ("PROBE as recorded (45)", PP, yp), ("PROBE with Args: (none)", PN, yp)):
        print(f"\n== {label}")
        votes = np.array([P[i] < thr[i] for i in range(n)])
        singles = [rates(votes[i], y) for i in range(n)]
        print(f"{'single seed (mean of ' + str(n) + ')':34s} acc {np.mean([s['acc'] for s in singles]):.1%} | recall {np.mean([s['recall'] for s in singles]):.1%} | false warnings {np.mean([s['fw'] for s in singles]):.1%}")
        for k in range(n, 0, -1):
            r = rates(votes.sum(0) >= k, y)
            out[f"{label}|{k}of{n}"] = r
            print(fmt(f"warn if >= {k} of {n} warn", r))
        zs = sigmoid(logit(P).mean(0))
        pdm = sigmoid(logit(np.array([r["dev_p"] for r in runs])).mean(0))
        print(fmt("mean-logit ensemble", rates(zs < acc_threshold(pdm, yd), y)))
    (FT / "vote_analysis.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
