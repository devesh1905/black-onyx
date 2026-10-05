"""Throwaway-grade fine-tune of the Laya English checkpoint on Pool A train, scored on Pool A dev / Pool B test.

Run with the CUDA venv:  D:\Buildathon-Toolkit\venv-cuda\Scripts\python.exe eval/finetune_laya.py [--layers 4] [--epochs 3]
Selection rule: pick the epoch by DEV accuracy; the test set is scored once, for that epoch (and for the untouched model).
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import random
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HOME", r"D:\Buildathon-Toolkit\hf-cache")
import numpy as np  # noqa: E402
import torch  # noqa: E402
from laya import Router  # noqa: E402
from laya.common import collate_items  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GENERIC = "Does this tool call fit the user's task?"
Q = {"g": {"type": "noul", "instructions": GENERIC}}


def load(name):
    return [json.loads(l) for l in (ROOT / "eval" / "data" / name).read_text(encoding="utf-8").splitlines() if l.strip()]


def encode(agent, rows):
    internal = {"g": agent._to_internal(Q["g"])}
    out = []
    for r in rows:
        it = agent._encode_state(r["state"], ["g"], internal)[0]
        it["label"] = 1 if r["expected"]["fit"] else 0
        out.append(it)
    return out


def batches(items, bs, pad, shuffle=False, rng=None):
    idx = list(range(len(items)))
    if shuffle:
        rng.shuffle(idx)
    for i in range(0, len(idx), bs):
        yield collate_items([[items[j]] for j in idx[i:i + bs]], pad)


@torch.no_grad()
def p_fit(model, items, pad, dev):
    model.eval()
    ps, ys = [], []
    for b in batches(items, 32, pad):
        with torch.autocast("cuda", dtype=torch.bfloat16):
            out = model(b["input_ids"].to(dev), b["attention_mask"].to(dev), b["marker_pos"].to(dev), b["marker_mask"].to(dev), b["qtype"].to(dev))
        ps += torch.softmax(out[0].float()[:, :2], -1)[:, 1].cpu().tolist()
        ys += b["label"].tolist()
    return np.array(ps), np.array(ys)


def best_thr(p, y):
    cands = np.unique(np.round(p, 4))
    accs = [((p >= t) == (y == 1)).mean() for t in cands]
    return float(cands[int(np.argmax(accs))])


def auc(p, y):
    pos, neg = p[y == 1], p[y == 0]
    return float(np.mean([(a > b) + 0.5 * (a == b) for a in pos for b in neg]))


def metrics(p, y, t):
    pred_fit = p >= t
    nofit, fit = y == 0, y == 1
    return {"acc": float((pred_fit == (y == 1)).mean()), "recall_nofit": float((~pred_fit[nofit]).mean()),
            "false_warn": float((~pred_fit[fit]).mean()), "auc": auc(p, y), "thr": t}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", type=int, default=4)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--bs", type=int, default=16)
    ap.add_argument("--seed", type=int, default=1905)
    ap.add_argument("--save", default=str(ROOT / ".scratch" / "ft" / "model.pt"))
    a = ap.parse_args()
    torch.manual_seed(a.seed)
    rng = random.Random(a.seed)
    agent = Router(max_loaded=1).load("english")
    m, dev, pad = agent.model, agent.device, agent.tok.pad_token_id
    train, dv, te = (encode(agent, load(f)) for f in ("train.jsonl", "dev.jsonl", "test.jsonl"))
    print(f"train {len(train)} dev {len(dv)} test {len(te)} | device {dev}", flush=True)

    # untouched model: threshold on dev, scored on test
    pd, yd = p_fit(m, dv, pad, dev)
    base_t = best_thr(pd, yd)
    pt, yt = p_fit(m, te, pad, dev)
    base = metrics(pt, yt, base_t)
    print("BEFORE  dev acc %.3f | TEST %s" % (metrics(pd, yd, base_t)["acc"], {k: round(v, 3) for k, v in base.items()}), flush=True)

    layers = list(m.encoder.layers)[-a.layers:] if a.layers else []
    for p in m.parameters():
        p.requires_grad = False
    mods = [m.head, m.type_emb, m.scorer] + layers
    for md in mods:
        for p in md.parameters():
            p.requires_grad = True
    params = [p for p in m.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=0.01)
    steps = a.epochs * ((len(train) + a.bs - 1) // a.bs)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=a.lr, total_steps=steps, pct_start=0.1)
    best = (-1, None, None, None)
    t0 = time.time()
    for ep in range(1, a.epochs + 1):
        m.train()
        tot = n = 0
        for b in batches(train, a.bs, pad, True, rng):
            with torch.autocast("cuda", dtype=torch.bfloat16):
                out = m(b["input_ids"].to(dev), b["attention_mask"].to(dev), b["marker_pos"].to(dev), b["marker_mask"].to(dev), b["qtype"].to(dev))
                loss = torch.nn.functional.cross_entropy(out[0].float()[:, :2], b["label"].to(dev))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
            tot += loss.item() * len(b["label"]); n += len(b["label"])
        pd, yd = p_fit(m, dv, pad, dev)
        t = best_thr(pd, yd)
        md = metrics(pd, yd, t)
        print(f"epoch {ep}: train loss {tot/n:.4f} | DEV acc {md['acc']:.3f} recall {md['recall_nofit']:.3f} fw {md['false_warn']:.3f} auc {md['auc']:.3f} thr {t:.3f} | {time.time()-t0:.0f}s", flush=True)
        if md["acc"] > best[0]:
            best = (md["acc"], ep, t, copy.deepcopy({k: v.detach().cpu() for k, v in m.state_dict().items()}))
    _, ep, t, sd = best
    m.load_state_dict(sd)
    pt, yt = p_fit(m, te, pad, dev)
    res = metrics(pt, yt, t)
    print(f"AFTER   chosen epoch {ep} (by dev) | TEST {({k: round(v, 3) for k, v in res.items()})}", flush=True)
    Path(a.save).parent.mkdir(parents=True, exist_ok=True)
    torch.save(sd, a.save)
    Path(a.save).with_suffix(".json").write_text(json.dumps({"before": base, "after": res, "epoch": ep, "layers": a.layers, "lr": a.lr,
                                                           "epochs": a.epochs, "seed": a.seed, "n_train": len(train)}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
