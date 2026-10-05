"""The fine-tuned Laya switch in the sidebar: hidden without weights, off by default, and the default run is unchanged."""
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"
REAL_V2 = Path(os.environ.get("BLACKONYX_LAYA_V2_DIR", r"D:\Buildathon-Toolkit\laya-ft")) / "v2.pt"


def _labels(at):
    return [t.label for t in at.sidebar.toggle]


def test_switch_hidden_without_weights(monkeypatch, tmp_path):
    monkeypatch.setenv("BLACKONYX_LAYA_V2_DIR", str(tmp_path))
    monkeypatch.delenv("BLACKONYX_LAYA_MODEL", raising=False)
    at = AppTest.from_file(APP_PATH, default_timeout=60)
    at.run()
    at.sidebar.selectbox(key="defence_sel").set_value("D3")
    at.run()
    assert not at.exception
    assert "Fine-tuned Laya (v2)" not in _labels(at)


def test_switch_hidden_for_rules_only_defence(monkeypatch):
    monkeypatch.delenv("BLACKONYX_LAYA_MODEL", raising=False)
    at = AppTest.from_file(APP_PATH, default_timeout=60)
    at.run()
    at.sidebar.selectbox(key="defence_sel").set_value("D2")
    at.run()
    assert not at.exception
    assert "Fine-tuned Laya (v2)" not in _labels(at)


@pytest.mark.skipif(not REAL_V2.exists(), reason="v2 weights are local only")
def test_switch_visible_and_off_by_default_with_weights(monkeypatch):
    monkeypatch.delenv("BLACKONYX_LAYA_MODEL", raising=False)
    at = AppTest.from_file(APP_PATH, default_timeout=60)
    at.run()
    at.sidebar.selectbox(key="defence_sel").set_value("D3")
    at.run()
    assert not at.exception
    sw = [t for t in at.sidebar.toggle if t.label == "Fine-tuned Laya (v2)"]
    assert sw and sw[0].value is False
