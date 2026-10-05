import os, sys, json
os.environ["HF_HUB_OFFLINE"] = "1"
import torch, numpy as np
sys.path[:0] = ["src", "."]
from blackonyx.laya_sentinel import find_default_checkpoint_path
import laya
from eval.ft_analysis import acc_threshold
agent = laya.Agent(find_default_checkpoint_path(), device="cpu")
orig = {k: v.detach().clone() for k, v in agent.model.state_dict().items()}
ft = torch.load(".scratch/ft/best_model.pt", map_location="cpu")
changed = {k: v for k, v in ft.items() if k in orig and not torch.equal(v.float(), orig[k].float())}
print(len(changed), "changed tensors of", len(ft)); print(sorted({k.split(".")[0] + "." + k.split(".")[1] for k in changed})[:12])
tops = sorted({int(k.split(".")[2]) for k in changed if k.startswith("encoder.layers.")}); print("encoder layers changed:", tops[0], "-", tops[-1])
n = sum(v.numel() for v in changed.values()); print("params", n / 1e6, "M")
r = json.load(open(".scratch/ft/final_seed1905.json"))
thr = acc_threshold(np.array(r["dev_p"]), np.array(r["dev_y"]))
out = "D:/Buildathon-Toolkit/laya-ft/v2.pt"
torch.save(changed, out)
json.dump({"version": "v2", "seed": 1905, "layers": 8, "lr": 5e-5, "epochs": 5, "threshold": thr, "test": r["test"], "dev_acc": r["dev"]["acc"]},
          open("D:/Buildathon-Toolkit/laya-ft/v2.json", "w"), indent=1)
print("threshold", thr, "saved", out, os.path.getsize(out) / 1e6, "MB")
