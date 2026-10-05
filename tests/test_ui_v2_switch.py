"""The sidebar has no fine-tuned Laya switch; v2 is only reachable through BLACKONYX_LAYA_MODEL, which is off by default."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"


def test_no_v2_switch_in_sidebar(monkeypatch):
    monkeypatch.delenv("BLACKONYX_LAYA_MODEL", raising=False)
    at = AppTest.from_file(APP_PATH, default_timeout=60)
    at.run()
    for d in ("D2", "D3", "D4"):
        at.sidebar.selectbox(key="defence_sel").set_value(d)
        at.run()
        assert not at.exception
        assert all("Fine-tuned" not in t.label for t in at.sidebar.toggle)
