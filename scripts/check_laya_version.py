import os, sys, json, time, numpy as np
sys.path[:0] = ["src", "."]
from blackonyx.laya_sentinel import LayaSentinel
from eval.calibrate_laya import load_dataset, extract_task_and_tool_from_state
import re
r = json.load(open(".scratch/ft/final_seed1905.json"))
thr = json.load(open("D:/Buildathon-Toolkit/laya-ft/v2.json"))["threshold"]
saved = np.array(r["test_p"]); y = np.array(r["test_y"])
s = LayaSentinel(model_version="v2")
print("version:", s.version, "| error:", s._v2_error)
rows = [json.loads(l) for l in open("eval/data/test.jsonl", encoding="utf-8")]
ps, ms = [], []
for row in rows:
    st = row["state"]
    task = re.search(r"User request: (.*)\nTool:", st, re.S).group(1)
    tool = re.search(r"\nTool: (.*)\nArgs:", st).group(1)
    argstr = st.split("\nArgs: ", 1)[1]
    args = {}
    for part in argstr.split(", "):
        if "=" in part:
            k, v = part.split("=", 1); args[k] = v
    res = s.score(task, tool, args)
    ps.append(res.score); ms.append(res.ms)
ps = np.array(ps)
warn = ps < thr; warn_saved = saved < thr
print("max |p - saved p|: %.4f | decision flips vs GPU run: %d / %d" % (np.abs(ps - saved).max(), (warn != warn_saved).sum(), len(ps)))
fit, nofit = y == 1, y == 0
print("CPU fp32 v2 on test: acc %.1f%% recall %.1f%% fw %.1f%% | median %.0f ms/call" % (100*((~warn) == fit).mean(), 100*warn[nofit].mean(), 100*warn[fit].mean(), np.median(ms)))
