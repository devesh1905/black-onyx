import json
import re

from app.ui import render_stage
from app.ui.panels import howitworks_html, load_results, results_html
from blackonyx.runner import run_scenario


def test_stage_is_self_contained_and_embeds_events():
    ev = run_scenario("L1", "A1", "D2")
    html = render_stage(ev, autoplay=False)
    assert not re.search(r"<script[^>]+src=|<link[^>]+href=|https?://(cdn|unpkg|cdnjs)", html)
    m = re.search(r"const EVENTS = (\[.*?\]);\nconst OPT", html, re.S)
    assert m and len(json.loads(m.group(1))) == len(ev)
    assert "prefers-reduced-motion" in html and 'aria-label="Replay position"' in html


def test_stage_handles_empty_and_hostile_text():
    assert "Pick a scenario" in render_stage([], autoplay=False)
    ev = run_scenario("L1", None, "D2", injected_text="</script><script>alert(1)</script>")
    assert "</script><script>alert(1)" not in render_stage(ev, autoplay=False)


def test_events_carry_ui_fields():
    ev = run_scenario("L1", "A1", "D0")
    assert any(e["type"] == "effect" and e["leak"] for e in ev) and ev[-1]["type"] == "summary"


def test_results_and_how_panels_render():
    r = load_results()
    assert r and "D2" in r["defences"]
    assert "Limits" in results_html(r) and "Control and data arguments" in howitworks_html()


def test_icons_are_inline_and_sized():
    from app.ui.icons import ICONS, svg
    ev = run_scenario("L1", "A1", "D2")
    html = render_stage(ev, autoplay=False)
    assert "{{ic:" not in html and "/*__ICONS__*/" not in html
    assert "<svg class=\"ic\"" in html and set(ICONS) >= {"shield-x", "maximize", "play"}
    assert "width=\"16\"" in svg("play", 16) and "#svg{" in html   # graph rule must not leak onto icon svgs
