"""Score the live-format probe set (eval/live_probe.py) with the original and the fine-tuned Laya (task F).

Run with the CUDA venv:  D:\\Buildathon-Toolkit\\venv-cuda\\Scripts\\python.exe eval/probe_score.py
Original uses the live threshold (src/blackonyx/laya_thresholds.json); the fine-tuned model uses a threshold fitted on DEV.
The probe set is small and is a format/distribution check, not a benchmark.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HOME", r"D:\Buildathon-Toolkit\hf-cache")

import numpy as np  # noqa: E402
import torch  # noqa: E402
from laya import Router  # noqa: E402

from finetune_laya import GENERIC, Q, best_thr, encode, load, p_fit  # noqa: E402

FT = ROOT / ".scratch" / "ft"


def main() -> None:
    probe = json.loads((FT / "probe.json").read_text(encoding="utf-8"))
    rows = [{"state": r["state"], "expected": {"fit": r["fit"]}} for r in probe]
    agent = Router(max_loaded=1).load("english")
    m, dev, pad = agent.model, agent.device, agent.tok.pad_token_id
    items = encode(agent, rows)
    dv = encode(agent, load("dev.jsonl"))
    live_thr = json.loads((ROOT / "src" / "blackonyx" / "laya_thresholds.json").read_text())["default"]["threshold"]

    def report(name, p, y, thr):
        warn = p < thr
        fw = warn[y == 1].mean()
        rec = warn[y == 0].mean()
        print(f"{name:12s} thr {thr:.3f} | false warnings {fw:.1%} ({int(warn[y == 1].sum())}/{int((y == 1).sum())}) | caught injected {rec:.1%} ({int(warn[y == 0].sum())}/{int((y == 0).sum())})")
        return {"name": name, "thr": float(thr), "fw": float(fw), "recall": float(rec)}

    out = []
    y = np.array([1 if r["fit"] else 0 for r in probe])
    p = np.array([float(agent.predict(r["state"], Q)["answers"]["g"]["noul"]) for r in probe])   # the live path's own scoring
    out.append(report("original", p, y, live_thr))
    sd = torch.load(FT / "best_model.pt", map_location="cpu")
    m.load_state_dict(sd)
    pd, yd = p_fit(m, dv, pad, dev)
    t = best_thr(pd, yd)
    p, y = p_fit(m, items, pad, dev)
    out.append(report("fine-tuned", p, y, t))
    for r, pp in zip(probe, p):
        if (pp < t) == r["fit"]:      # a miss in either direction
            print("  MISS", "fit" if r["fit"] else "no-fit", f"p={pp:.2f}", repr(r["state"][:110]))
    (FT / "probe_result.json").write_text(json.dumps(out), encoding="utf-8")


if __name__ == "__main__":
    main()
