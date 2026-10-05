"""Train 5 seeds of the dev-chosen config (8 layers, lr 5e-5, 5 epochs) and save, per seed, the dev / test / live-probe scores.

Run with the CUDA venv:  D:\\Buildathon-Toolkit\\venv-cuda\\Scripts\\python.exe eval/finetune_seeds.py
Writes .scratch/ft/final_seed<N>.json (dev_p, test_p, probe_p, probe_p_none). The probe is scored twice: as recorded, and with
an empty "Args: " rewritten to "Args: (none)". Seeds and epoch are chosen on DEV only; test is scored once per seed.
"""
from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import torch  # noqa: E402
from laya import Router  # noqa: E402

from finetune_laya import batches, best_thr, encode, load, metrics, p_fit  # noqa: E402
from notify import notify  # noqa: E402

OUT = ROOT / ".scratch" / "ft"
SEEDS = [1905, 7, 42, 11, 2024]
LAYERS, LR, EPOCHS = 8, 5e-5, 5


def main() -> None:
    agent = Router(max_loaded=1).load("english")
    m, dev, pad = agent.model, agent.device, agent.tok.pad_token_id
    train, dv, te = (encode(agent, load(f)) for f in ("train.jsonl", "dev.jsonl", "test.jsonl"))
    probe = json.loads((OUT / "probe.json").read_text(encoding="utf-8"))
    pr = encode(agent, [{"state": r["state"], "expected": {"fit": r["fit"]}} for r in probe])
    pr_none = encode(agent, [{"state": r["state"].replace("Args: ", "Args: (none)") if r["state"].endswith("Args: ") else r["state"],
                              "expected": {"fit": r["fit"]}} for r in probe])
    original = {k: v.detach().cpu().clone() for k, v in m.state_dict().items()}
    t0 = time.time()
    for seed in SEEDS:
        m.load_state_dict(original)
        torch.manual_seed(seed)
        rng = random.Random(seed)
        for p in m.parameters():
            p.requires_grad = False
        for md in [m.head, m.type_emb, m.scorer] + list(m.encoder.layers)[-LAYERS:]:
            for p in md.parameters():
                p.requires_grad = True
        params = [p for p in m.parameters() if p.requires_grad]
        opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.01)
        sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=LR, total_steps=EPOCHS * ((len(train) + 15) // 16), pct_start=0.1)
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
            md = metrics(pd, yd, best_thr(pd, yd))
            if md["acc"] > best["acc"]:
                best = {"acc": md["acc"], "epoch": ep, "dev": md, "dev_p": pd.tolist(), "dev_y": yd.tolist(),
                        "state": {k: v.detach().cpu().clone() for k, v in m.state_dict().items()}}
        m.load_state_dict(best.pop("state"))
        pt, yt = p_fit(m, te, pad, dev)
        pp, ypr = p_fit(m, pr, pad, dev)
        pn, _ = p_fit(m, pr_none, pad, dev)
        tm = metrics(pt, yt, best["dev"]["thr"])
        rec = {"seed": seed, "layers": LAYERS, "lr": LR, "epochs": EPOCHS, "epoch": best["epoch"], "dev": best["dev"], "test": tm,
               "dev_p": best["dev_p"], "dev_y": best["dev_y"], "test_p": pt.tolist(), "test_y": yt.tolist(),
               "probe_p": pp.tolist(), "probe_p_none": pn.tolist(), "probe_y": ypr.tolist()}
        (OUT / f"final_seed{seed}.json").write_text(json.dumps(rec), encoding="utf-8")
        notify("Laya seeds", f"seed {seed} done: TEST acc {tm['acc']:.1%} recall {tm['recall_nofit']:.1%} FW {tm['false_warn']:.1%} ({time.time()-t0:.0f}s)")
        print(f"seed {seed}: epoch {best['epoch']} | TEST acc {tm['acc']:.3f} recall {tm['recall_nofit']:.3f} fw {tm['false_warn']:.3f} | {time.time()-t0:.0f}s", flush=True)
    notify("Laya seeds", "all seeds done", wait=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
