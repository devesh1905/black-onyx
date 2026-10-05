"""Laya versions table (v0 to v3), shared by the Results tab and docs/judge-prompts/index.html.

Every value is a measured number: held-out set of 400 call-fit pairs, thresholds fitted on dev only
(docs/laya-finetune.md, docs/laya-results.md); latency timed on this laptop.
"""
from __future__ import annotations

import html

LAYA_COLS = ["v0", "v1", "v2", "v2+kw", "v3"]
LAYA_ROWS = [
    ("What it is", ["Original", "4 layers", "8 layers", "8 + kw", "5-seed vote"], None),
    ("Accuracy", ["81.0%", "90.5%", "90.9%", "92.9%", "95.2%"], 4),
    ("Recall (bad calls)", ["77.0%", "96.0%", "98.6%", "98.5%", "98.0%"], 2),
    ("False warnings", ["15.0%", "15.0%", "16.7%", "12.7%", "7.5%"], 4),
    ("AUC", ["0.857", "0.947", "0.984*", "n/a", "n/a"], 2),
    ("Live check: false warnings", ["31.0%", "n/m", "28.3%", "n/m", "17.2%"], 4),
    ("Live check: calls caught", ["68.8%", "n/m", "95.0%", "n/m", "93.8%"], 2),
    ("Latency, CPU", ["288 ms", "288 ms", "288 ms", "288 ms", "1.15 s"], 0),
    ("Latency, GPU", ["32 ms", "32 ms", "32 ms", "32 ms", "161 ms"], 0),
    ("In the demo", ["Yes", "No", "No", "No", "No"], None),
]
LAYA_NOTES = [
    "Columns: v0 = original checkpoint (live on the site); v1 = top 4 layers, 3 epochs; v2 = top 8 layers, lr 5e-5 (mean of 5 seeds); "
    "v2+kw = v2 plus the keyword score (mean of 3 seeds); v3 = five-seed unanimous vote of v2. n/m = not measured. "
    "Live check = the 45-state runtime-format check. GPU = RTX 4050.",
    "Only v0 runs in the demo. v2 can be enabled with an environment setting (off by default); v3 would need a shared-trunk build, and its weights were not saved.",
    "All versions are scored on the same frozen held-out set of 400 call-fit pairs (different templates from the 1,600 training pairs). "
    "The test set was never used for tuning; every choice (layers, learning rate, epoch, threshold) was made on dev.",
    "v2 and v3 use five seeds (1905, 7, 42, 11, 2024). v3 warns only when all five models agree. Intervals at N=200 are wide: "
    "7.5% false warnings is roughly 4.6% to 12%.",
    "*AUC for v2 is the mean of three seeds.",
    "Latency: median over 20 real states, original weights. The fine-tuned versions have the same size, so the same cost. "
    "The v3 figure is five models run one after another. Running all five at once needs more RAM than this laptop has free, "
    "so a deployment would share the 20 frozen bottom layers.",
    "The live-format check is 45 states recorded from real runs (29 legitimate, 16 injected), so it is a small sample. "
    "It shows the next gap: the training data has no calls with empty arguments, so those get flagged. "
    "The fix is more training data covering runtime-style calls.",
    "v1, v2+kw and v3 are not wired into the site; v2 is opt-in through an environment setting and the live app runs v0.",
]


CSS = """
.best{color:#bbf7d0;font-weight:600;background:rgba(53,208,127,.07)}
table.ver th:first-child{width:25%}
table.ver td,table.ver th{font-size:12.5px}
.notes{color:var(--t2);font-size:12px;margin:10px 0 0;padding-left:18px}.notes li{margin:3px 0}
"""


def versions_table_html() -> str:
    head = "".join(f'<th scope="col">{html.escape(c)}</th>' for c in LAYA_COLS)
    rows = []
    for label, vals, best in LAYA_ROWS:
        tds = "".join(f'<td class="{"best" if best == i else ""}">{html.escape(v)}</td>' for i, v in enumerate(vals))
        rows.append(f'<tr><th scope="row">{html.escape(label)}</th>{tds}</tr>')
    return f'<table class="ver"><thead><tr><th scope="col">Measure</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>'


def notes_html() -> str:
    return "<ul class=\"notes\">" + "".join(f"<li>{html.escape(n)}</li>" for n in LAYA_NOTES) + "</ul>"


def versions_panel_html() -> str:
    """Self-contained snippet for the Results tab (uses the BASE_CSS variables of app/ui/panels.py)."""
    return f"<style>{CSS}</style><div class=\"panel\"><h2>Our fine-tuned versions of Laya</h2>{versions_table_html()}{notes_html()}</div>"


def versions_page_html() -> str:
    """The panel wrapped in the same page shell as the other Results-tab components."""
    from .panels import _page
    return _page(versions_panel_html())
