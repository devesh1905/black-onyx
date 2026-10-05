"""Post-hoc analysis of the fine-tuned Laya scores: false-warning budget (A), stacking with the keyword score (B),
temperature calibration (D). Reads .scratch/ft/final_seed*.json (written by eval/finetune_sweep.py). No GPU needed.

Every fit uses DEV only; the test numbers are read off once.

    python -m eval.ft_analysis
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from eval.calibrate_laya import load_dataset, score_keyword_baseline  # noqa: E402
from eval.laya_ladder import apply_logreg, fit_logreg  # noqa: E402

FT = ROOT / ".scratch" / "ft"


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


def metrics(p, y, t):
    p, y = np.asarray(p), np.asarray(y)
    warn = p < t
    fit, nofit = y == 1, y == 0
    return {"acc": float(((~warn) == fit).mean()), "recall": float(warn[nofit].mean()), "fw": float(warn[fit].mean())}


def ece(p, y, bins=10):
    p, y = np.asarray(p), np.asarray(y)
    edges = np.linspace(0, 1, bins + 1)
    tot = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi) if hi < 1 else (p >= lo) & (p <= hi)
        if m.any():
            tot += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(tot)


def acc_threshold(p, y):
    best, bt = -1, 0.5
    for t in np.unique(np.round(p, 4)):
        a = metrics(p, y, t)
        bal = (a["recall"] + 1 - a["fw"]) / 2
        if bal > best:
            best, bt = bal, float(t)
    return bt


def budget_threshold(p, y, budget):
    best = None
    for t in np.unique(np.round(p, 4)):
        m = metrics(p, y, t)
        if m["fw"] <= budget and (best is None or m["recall"] > best[1] or (m["recall"] == best[1] and t > best[0])):
            best = (float(t), m["recall"])
    return best[0] if best else 0.0


def fit_temperature(p, y):
    z, yy = logit(p), np.asarray(y, float)
    best, bt = 1e9, 1.0
    for T in np.linspace(0.3, 6, 115):
        q = np.clip(sigmoid(z / T), 1e-6, 1 - 1e-6)
        nll = -(yy * np.log(q) + (1 - yy) * np.log(1 - q)).mean()
        if nll < best:
            best, bt = nll, float(T)
    return bt


def kw_scores(items):
    return np.array([score_keyword_baseline([it])[0][0] for it in items], float)


def pct(x):
    return f"{100 * x:.1f}%"


def main() -> None:
    dev_items = load_dataset(ROOT / "eval/data/dev.jsonl")
    test_items = load_dataset(ROOT / "eval/data/test.jsonl")
    kd, kt = kw_scores(dev_items), kw_scores(test_items)
    runs = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(FT.glob("final_seed*.json"))]
    runs.sort(key=lambda r: r["dev"]["acc"], reverse=True)
    rows = []
    print(f"config: layers={runs[0]['layers']} lr={runs[0]['lr']:g} epochs={runs[0]['epochs']} | seeds {[r['seed'] for r in runs]}")
    for r in runs:
        pd, yd, pt, yt = map(np.array, (r["dev_p"], r["dev_y"], r["test_p"], r["test_y"]))
        t0 = acc_threshold(pd, yd)
        base = metrics(pt, yt, t0)
        line = {"seed": r["seed"], "dev_acc": r["dev"]["acc"], "base": base, "thr": t0, "auc_dev": r["dev"]["auc"], "auc_test": r["test"]["auc"]}
        for b in (0.10, 0.08):
            tb = budget_threshold(pd, yd, b)
            line[f"budget{int(b * 100)}"] = {**metrics(pt, yt, tb), "thr": tb}
        # B: stack logit(p) with the keyword score, logistic fit on dev
        Xd = [[float(a), float(k), 1.0] for a, k in zip(logit(pd), kd)]
        Xt = [[float(a), float(k), 1.0] for a, k in zip(logit(pt), kt)]
        w = fit_logreg(Xd, [int(v) for v in yd])
        sd, st = np.array(apply_logreg(w, Xd)), np.array(apply_logreg(w, Xt))
        ts = acc_threshold(sd, yd)
        line["stack"] = {**metrics(st, yt, ts), "thr": ts}
        tsb = budget_threshold(sd, yd, 0.10)
        line["stack_budget10"] = {**metrics(st, yt, tsb), "thr": tsb}
        # D: temperature scaling on dev
        T = fit_temperature(pd, yd)
        line["T"] = T
        line["ece_before"], line["ece_after"] = ece(pt, yt), ece(sigmoid(logit(pt) / T), yt)
        rows.append(line)
        print(f"seed {r['seed']}: dev acc {pct(r['dev']['acc'])} | TEST base acc {pct(base['acc'])} rec {pct(base['recall'])} fw {pct(base['fw'])} "
              f"| budget10 rec {pct(line['budget10']['recall'])} fw {pct(line['budget10']['fw'])} acc {pct(line['budget10']['acc'])} "
              f"| stack acc {pct(line['stack']['acc'])} rec {pct(line['stack']['recall'])} fw {pct(line['stack']['fw'])} "
              f"| stack+budget10 rec {pct(line['stack_budget10']['recall'])} fw {pct(line['stack_budget10']['fw'])} "
              f"| T={T:.2f} ECE {line['ece_before']:.3f}->{line['ece_after']:.3f}")
    (FT / "analysis.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")

    def mean(key, sub):
        return np.mean([r[key][sub] for r in rows])
    print("\nMEAN over seeds (test):")
    for key in ("base", "budget10", "budget8", "stack", "stack_budget10"):
        print(f"  {key:15s} acc {pct(mean(key, 'acc'))} recall {pct(mean(key, 'recall'))} fw {pct(mean(key, 'fw'))}")
    print(f"  ECE before {np.mean([r['ece_before'] for r in rows]):.3f} after {np.mean([r['ece_after'] for r in rows]):.3f}")


if __name__ == "__main__":
    main()
