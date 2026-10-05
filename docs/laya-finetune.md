# Laya fine-tune: sweep, calibration and live-format check (5 Oct)

Scripts: `eval/finetune_sweep.py` (GPU), `eval/ft_analysis.py`, `eval/live_probe.py`, `eval/probe_score.py`. Not part of the demo build:
the weights (1.7 GB) are not in the repository and the live sentinel is unchanged.

## 1. Sweep (dev only) and three seeds (test, scored once)

Last 4 or 8 encoder layers plus the head, lr 1e-5 / 2e-5 / 5e-5, 5 epochs, trained on the 1,600 Pool A pairs. Dev accuracy saturates
(92.7% to 99.5%) because dev shares templates with train, so dev cannot separate the good configs. The dev-best config
(8 layers, lr 5e-5) was retrained with 3 seeds and scored once on the held-out Pool B test set (N=400):

| Seed | Test accuracy | Recall on no-fit | False-warning rate | AUC |
|---|---|---|---|---|
| 1905 | 90.8% | 98.5% | 17.0% | 0.986 |
| 7 | 91.8% | 98.5% | 15.0% | 0.985 |
| 42 | 88.5% | 99.0% | 22.0% | 0.980 |
| mean | 90.3% | 98.7% | 18.0% | 0.984 |

Ranking is much better than before (AUC 0.857 for the original, 0.947 for the first 4-layer fine-tune). The weak point is the threshold.

## 2. Threshold, stacking, calibration (fit on dev, read off on test)

| Method | Test accuracy | Recall | False warnings |
|---|---|---|---|
| dev-fitted threshold (mean of 3 seeds) | 90.3% | 98.7% | 18.0% |
| false-warning budget of 10% fitted on dev | 86.3% | 99.7% | 27.0% |
| stacked with the keyword score (mean) | 92.9% | 98.5% | 12.7% (6.0% to 15.0% by seed) |

* **The budget threshold does not transfer.** Dev is saturated, so a 10% budget is met at an extreme threshold and then over-warns on test (27%).
* **Stacking helps unevenly:** one seed reaches 96.2% accuracy and 6.0% false warnings, the other two are unchanged.
* **Calibration:** temperature scaling (T about 1.6) moves ECE from 0.066 to 0.061; the ECE gate (<= 0.10) is already met without it.
* Gates on test: accuracy >= 90% met (90.3% to 92.9%), recall >= 90% met, ECE met, **false-warning <= 10% not met.**

## 3. Live-format check (the probe set)

`eval/live_probe.py` records the states the sentinel really sees at run time (45 unique states: 29 legitimate, 16 injected).

| Model | Threshold | False warnings | Injected calls caught |
|---|---|---|---|
| original (live setting) | 0.32 | 31.0% (9/29) | 68.8% (11/16) |
| fine-tuned | 0.98 (dev-fitted) | 31.0% (9/29) | 93.8% (15/16) |

Two gaps explain why the test-set gain does not carry over yet:
1. **No empty-argument calls in the training data** (0 of 1,600). Real calls such as `read_inbox` with no arguments get p close to 0, so
   every one is a false warning.
2. **The dev-fitted threshold (0.98) is an artefact of the saturated dev set.**

Small probe (N=45): a format check, not a benchmark. Next step is option E: harder, more varied training data that includes runtime-style
and empty-argument calls, and a threshold fitted on a dev set that does not share templates with train.
