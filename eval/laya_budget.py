"""Pick the Laya threshold for a false-warning BUDGET instead of for balanced accuracy (dev only), report on the test set.

    python -m eval.laya_budget            # reads the cached scores in eval/data/laya_scores.json, no re-scoring
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from eval.calibrate_laya import calculate_metrics, load_dataset  # noqa: E402
from eval.laya_ladder import METHODS, apply_logreg, fit_logreg, stack_features  # noqa: E402

BUDGETS = (0.05, 0.08, 0.10)


def budget_threshold(scores, labels, budget):
    """Highest-recall threshold whose DEV false-warning rate is <= budget."""
    best = None
    for ti in range(1, 100):
        t = ti / 100
        m = calculate_metrics(scores, labels, threshold=t)
        if m["false_warning_rate"] <= budget and (best is None or m["recall_no_fit"] > best[1] or
                                                  (m["recall_no_fit"] == best[1] and t > best[0])):
            best = (t, m["recall_no_fit"])
    return best[0] if best else 0.01


def main() -> None:
    dev, test = load_dataset(ROOT / "eval/data/dev.jsonl"), load_dataset(ROOT / "eval/data/test.jsonl")
    dl = [1 if x["expected"]["fit"] else 0 for x in dev]
    tl = [1 if x["expected"]["fit"] else 0 for x in test]
    cache = json.loads((ROOT / "eval/data/laya_scores.json").read_text(encoding="utf-8"))
    cands = {"generic question": (lambda s: METHODS["generic question"](s))}
    w = fit_logreg(stack_features(cache["dev"], dev), dl)
    out = ["| Method | FW budget (dev) | Threshold | Test accuracy | Test recall on no-fit | Test false-warning rate |", "|---|---|---|---|---|---|"]
    for name, fn in cands.items():
        d, t = [fn(s) for s in cache["dev"]], [fn(s) for s in cache["test"]]
        for b in BUDGETS:
            thr = budget_threshold(d, dl, b)
            m = calculate_metrics(t, tl, threshold=thr)
            out.append(f"| {name} | {b:.0%} | {thr:.2f} | {m['accuracy']:.1%} | {m['recall_no_fit']:.1%} | {m['false_warning_rate']:.1%} |")
    d, t = apply_logreg(w, stack_features(cache["dev"], dev)), apply_logreg(w, stack_features(cache["test"], test))
    for b in BUDGETS:
        thr = budget_threshold(d, dl, b)
        m = calculate_metrics(t, tl, threshold=thr)
        out.append(f"| stacked (Laya + keyword) | {b:.0%} | {thr:.2f} | {m['accuracy']:.1%} | {m['recall_no_fit']:.1%} | {m['false_warning_rate']:.1%} |")
    print("\n".join(out))


if __name__ == "__main__":
    main()
