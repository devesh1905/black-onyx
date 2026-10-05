import os, sys, json, time, statistics as st
os.environ["HF_HUB_OFFLINE"]="1"; os.environ.setdefault("HF_HOME", r"D:\Buildathon-Toolkit\hf-cache")
import laya
dev = sys.argv[1]
agent = laya.Agent("convaiinnovations/laya", device=dev)
probe = json.load(open(".scratch/ft/probe.json", encoding="utf-8"))
states = [r["state"] for r in probe][:20]
Q = {"g": {"type": "noul", "instructions": "Does this tool call fit the user's task?"}}
for s in states[:3]: agent.predict(s, Q)          # warm-up
def timeit(k):
    ts = []
    for s in states:
        t = time.perf_counter()
        for _ in range(k): agent.predict(s, Q)
        ts.append((time.perf_counter() - t) * 1000)
    return st.median(ts)
print(dev, "1 model: %.0f ms | 5 models sequential: %.0f ms" % (timeit(1), timeit(5)))
