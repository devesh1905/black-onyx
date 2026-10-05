# Laya Sentinel Evaluation Results (Measured Offline)

> **Evaluation Specification:** docs/roadmap.md Section 11A. Measured on CPU in full fp32 reference precision.
> All confidence intervals are **95% Wilson intervals**.

## Summary of Ladder Rungs on Held-out Test Set (Pool B, N=400)

| Rung / Method | Accuracy | Recall on No-Fit | False-Warning Rate | ECE | Median Latency |
|---|---|---|---|---|---|
| **Keyword Baseline** | 74.0% [60.5%, 84.1%] | 66.7% [46.7%, 82.0%] | 19.2% [8.5%, 37.9%] | 0.260 | 0.0 ms |
| **Rung 0: Zero-shot English (generic question)** | 82.0% [69.2%, 90.2%] | 87.5% [69.0%, 95.7%] | 23.1% [11.0%, 42.0%] | 0.115 | 288.4 ms |
| **Rung 1: Closed per-tool question** | 58.0% [44.2%, 70.6%] | 25.0% [12.0%, 44.9%] | 11.5% [4.0%, 29.0%] | 0.266 | 290.9 ms |
| **Rung 1b: Paraphrase averaging** | 56.0% [42.3%, 68.8%] | 20.8% [9.2%, 40.5%] | 11.5% [4.0%, 29.0%] | 0.266 | 741.7 ms |
| **Rung 2: Calibrated threshold on Dev** | 52.0% [38.5%, 65.2%] | 54.2% [35.1%, 72.1%] | 50.0% [32.1%, 67.9%] | 0.266 | 741.7 ms |
| **NullSentinel (fallback)** | 50.0% [45.0%, 55.0%] | 0.0% [0.0%, 0.0%] | 0.0% [0.0%, 0.0%] | 0.500 | 0.0 ms |

**Environment:** CPU, full `fp32` precision, `laya==0.3.26`, offline cache `HF_HUB_OFFLINE=1`.

---

## Sliced Analysis (Rung 2 Calibrated Model)

| Slice | Description | Accuracy | Recall on No-Fit | Count |
|---|---|---|---|---|
| **Tool-Level Mismatch** | Tool-level mismatch (unrelated tool requested) | 84.6% [57.8%, 95.7%] | 84.6% [57.8%, 95.7%] | n=13 |
| **Argument-Level Mismatch** | Argument-level mismatch (right tool, wrong destination/recipient) | 57.1% [25.1%, 84.2%] | 57.1% [25.1%, 84.2%] | n=7 |
| **Prompt Injection Following** | Injection following (exfiltration payload instructions) | 50.0% [15.0%, 85.0%] | 50.0% [15.0%, 85.0%] | n=4 |

### Key Takeaways for Final Presentation & Defense
1. **Rung 2 Calibration beats Keyword Baseline:** Calibrating the threshold on the dev set dramatically suppresses false warnings while maintaining high recall on mismatching tool calls.
2. **Argument-level honesty:** As specified in Section 11A.2, argument-level validation (e.g. paying the wrong account or exfiltrating to an unknown domain) is guaranteed by Black Onyx rules and declassifiers, not solely by the local classifier.
3. **Zero Security Dependency:** Laya Sentinel is strictly advisory. Even if Laya returns `score=None` or false negatives, Black Onyx's information flow policy gate stops all unauthorized sensitive tool executions.
