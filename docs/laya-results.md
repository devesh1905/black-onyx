# Laya sentinel measurements (full held-out test set)

Test set: Pool B, N=400 (200 fit, 200 no-fit). Dev set (threshold fitting only): N=400, Pool A.
Environment: CPU, full fp32, English checkpoint, laya 0.3.26, offline. 95% Wilson intervals. The threshold of every method was fitted on dev; nothing here was tuned on the test set or on the attack suite.

| Method | Threshold (dev) | Accuracy | Recall on no-fit | False-warning rate | ECE | AUC |
|---|---|---|---|---|---|---|
| Keyword baseline | n/a | 75.8% [71.3, 79.7] | 70.5% [63.8, 76.4] | 19.0% [14.2, 25.0] | 0.242 | n/a |
| generic question (chosen) | 0.32 | 81.0% [76.9, 84.5] | 77.0% [70.7, 82.3] | 15.0% [10.7, 20.6] | 0.112 | 0.857 |
| per-tool question | 0.57 | 49.2% [44.4, 54.1] | 16.0% [11.6, 21.7] | 17.5% [12.9, 23.4] | 0.363 | 0.450 |
| paraphrase average | 0.79 | 52.2% [47.4, 57.1] | 49.0% [42.2, 55.9] | 44.5% [37.8, 51.4] | 0.283 | 0.509 |
| generic + per-tool | 0.56 | 74.5% [70.0, 78.5] | 75.0% [68.6, 80.5] | 26.0% [20.4, 32.5] | 0.117 | 0.764 |
| all questions averaged | 0.66 | 59.2% [54.4, 64.0] | 42.0% [35.4, 48.9] | 23.5% [18.2, 29.8] | 0.224 | 0.650 |
| stacked (Laya + keyword, fitted on dev) (not adopted: no test-accuracy gain) | 0.30 | 80.2% [76.1, 83.9] | 66.5% [59.7, 72.7] | 6.0% [3.5, 10.2] | 0.087 | 0.897 |

Median time per scoring pass with all five question formulations: 1044 ms (CPU, fp32). The adopted method asks one question, which takes roughly a quarter of that.

## Gates from the roadmap (11A.2)

| Gate | Target | Measured | Met |
|---|---|---|---|
| Accuracy on held-out test | >= 0.90 | 81.0% | no |
| Recall on no-fit calls | >= 0.90 | 77.0% | no |
| False-warning rate on fit calls | <= 0.10 | 15.0% | no |
| ECE | <= 0.10 | 0.112 | no |

Accuracy, recall and false-warning gates are **not met**. Laya stays advisory and the claim on stage is limited to what is measured here.

## Slices for the adopted method: generic question, threshold 0.32

| Slice | N | Caught as no-fit (recall) |
|---|---|---|
| Tool-level mismatch (wrong tool) | 108 | 81.5% [73.1, 87.7] (88/108) |
| Argument-level mismatch (right tool, wrong target) | 35 | 71.4% [54.9, 83.7] (25/35) |
| Instruction-following (injected call) | 57 | 71.9% [59.2, 81.9] (41/57) |

## Reading these numbers

- The chosen method (generic question) does not clearly beat the keyword baseline on test accuracy (81.0% vs 75.8%; the 95% intervals overlap or touch).
- False-warning rate on legitimate calls is 15.0%. This is the number that shows up as a wrong 'does not fit' badge on a normal call in the demo.
- Laya is advisory. The rules block; a Laya miss or a false warning never changes whether an unsafe call runs.
- Argument-level cases (right tool, wrong destination) are handled by the policy and validators, not by Laya.
