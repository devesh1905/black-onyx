"""Small hyper-parameter sweep for the Laya fine-tune, then 3 seeds of the dev-best config, scored once on test.

Run with the CUDA venv:  D:\\Buildathon-Toolkit\\venv-cuda\\Scripts\\python.exe eval/finetune_sweep.py

Rules: every choice (config, epoch, seed) is made on DEV only. The test set (Pool B) is scored only for the final
seeds of the chosen config. Probabilities are saved so the threshold / stacking / calibration analysis can be redone
without retraining:  .scratch/ft/final_seed<N>.json  and  .scratch/ft/best_model.pt
"""
from __future__ import annotations

import copy
import itertools
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from laya import Router  # noqa: E402

from finetune_laya import batches, best_thr, encode, load, metrics, p_fit  # noqa: E402
from notify import notify  # noqa: E402

OUT = ROOT / ".scratch" / "ft"
OUT.mkdir(parents=True, exist_ok=True)
GRID = {"layers": [4, 8], "lr": [1e-5, 2e-5, 5e-5]}
EPOCHS = 5
SEEDS = [1905, 7, 42]


def main() -> None:
    agent = Router(max_loaded=1).load("english")
    m, dev, pad = agent.model, agent.device, agent.tok.pad_token_id
    train, dv, te = (encode(agent, load(f)) for f in ("train.jsonl", "dev.jsonl", "test.jsonl"))
    original = {k: v.detach().cpu().clone() for k, v in m.state_dict().items()}
    print(f"train {len(train)} dev {len(dv)} test {len(te)} | device {dev}", flush=True)

    def train_cfg(layers: int, lr: float, seed: int, keep_state: bool = False):
        m.load_state_dict(original)
        torch.manual_seed(seed)
        rng = random.Random(seed)
        for p in m.parameters():
            p.requires_grad = False
        mods = [m.head, m.type_emb, m.scorer] + list(m.encoder.layers)[-layers:]
        for md in mods:
            for p in md.parameters():
                p.requires_grad = True
        params = [p for p in m.parameters() if p.requires_grad]
        opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.01)
        steps = EPOCHS * ((len(train) + 15) // 16)
        sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps, pct_start=0.1)
        best = {"acc": -1.0}
        for ep in range(1, EPOCHS + 1):
            m.train()
            for b in batches(train, 16, pad, True, rng):
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    out = m(b["input_ids"].to(dev), b["attention_mask"].to(dev), b["marker_pos"].to(dev), b["marker_mask"].to(dev), b["qtype"].to(dev))
                    loss = torch.nn.functional.cross_entropy(out[0].float()[:, :2], b["label"].to(dev))
                loss.backward()
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
            pd, yd = p_fit(m, dv, pad, dev)
            t = best_thr(pd, yd)
            md = metrics(pd, yd, t)
            if md["acc"] > best["acc"]:
                best = {"acc": md["acc"], "epoch": ep, "dev": md, "dev_p": pd.tolist(), "dev_y": yd.tolist()}
                if keep_state:
                    best["state"] = {k: v.detach().cpu().clone() for k, v in m.state_dict().items()}
        return best

    t0 = time.time()
    results = []
    for layers, lr in itertools.product(GRID["layers"], GRID["lr"]):
        r = train_cfg(layers, lr, SEEDS[0])
        results.append((r["acc"], layers, lr, r["epoch"], r["dev"]["auc"]))
        notify("Laya sweep", f"layers={layers} lr={lr:g}: best dev acc {r['acc']:.3f}")
        print(f"cfg layers={layers} lr={lr:g}: best dev acc {r['acc']:.3f} (epoch {r['epoch']}, auc {r['dev']['auc']:.3f}) | {time.time()-t0:.0f}s", flush=True)
    results.sort(reverse=True)
    _, layers, lr, _, _ = results[0]
    print(f"CHOSEN on dev: layers={layers} lr={lr:g}", flush=True)

    finals = []
    for seed in SEEDS:
        r = train_cfg(layers, lr, seed, keep_state=True)
        sd = r.pop("state")
        m.load_state_dict(sd)
        pt, yt = p_fit(m, te, pad, dev)
        t = r["dev"]["thr"]
        tm = metrics(pt, yt, t)
        rec = {"seed": seed, "layers": layers, "lr": lr, "epochs": EPOCHS, "epoch": r["epoch"], "dev": r["dev"], "test": tm,
               "dev_p": r["dev_p"], "dev_y": r["dev_y"], "test_p": pt.tolist(), "test_y": yt.tolist()}
        (OUT / f"final_seed{seed}.json").write_text(json.dumps(rec), encoding="utf-8")
        finals.append((r["acc"], seed, sd))
        print(f"seed {seed}: epoch {r['epoch']} | dev acc {r['dev']['acc']:.3f} | TEST acc {tm['acc']:.3f} recall {tm['recall_nofit']:.3f} "
              f"fw {tm['false_warn']:.3f} auc {tm['auc']:.3f} | {time.time()-t0:.0f}s", flush=True)
    finals.sort(key=lambda x: x[0], reverse=True)
    torch.save(finals[0][2], OUT / "best_model.pt")
    (OUT / "best_model.json").write_text(json.dumps({"seed": finals[0][1], "layers": layers, "lr": lr, "epochs": EPOCHS}), encoding="utf-8")
    notify("Laya sweep", f"done; best seed by dev: {finals[0][1]}", wait=True)
    print("done; best seed by dev:", finals[0][1], flush=True)


if __name__ == "__main__":
    main()
