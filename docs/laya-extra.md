# Laya: two extra experiments (5 Oct, not in the live demo path)

Both use the same held-out Pool B test set (N=400) and keep the Pool A dev set for any choice. The live sentinel is
unchanged: original English checkpoint, generic question, threshold from `laya_thresholds.json`.

## 1. Threshold for a false-warning budget (no re-scoring, `python -m eval.laya_budget`)

| Method | FW budget (dev) | Test accuracy | Test recall on no-fit | Test false-warning rate |
|---|---|---|---|---|
| generic question (live) | 5% | 77.0% | 62.5% | 8.5% |
| generic question (live) | 10% | 79.5% | 69.5% | 10.5% |
| stacked (Laya + keyword) | 5% | 80.8% | 67.5% | 6.0% |
| stacked (Laya + keyword) | 10% | 82.5% | 73.0% | 8.0% |

Reading: the stacked score is the only setting that meets the 10% false-warning gate on test (8.0%), at the price of about
4 points of recall against the live setting (73.0% vs 77.0%). The accuracy difference (82.5% vs 81.0%) is inside the
intervals, so by the ladder rule we did not switch the live path.

## 2. Fine-tune (`eval/finetune_laya.py`, GPU, about 1 minute)

Last 4 encoder layers plus the decision head, trained on the 1,600 Pool A pairs; the epoch was picked on dev, the test set
was scored once. Same scoring method before and after (threshold fitted on dev).

| | Before | After |
|---|---|---|
| Accuracy | 80.8% | 90.5% |
| Recall on no-fit | 77.0% | 96.0% |
| False-warning rate | 15.5% | 15.0% |
| AUC | 0.857 | 0.947 |

Dev accuracy was 94.8% against 90.5% on test, so part of the gain is specific to the training templates. The weights
(1.7 GB) are not in the repository, so this is not part of the demo build.
