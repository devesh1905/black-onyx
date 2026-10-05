"""The fine-tuned Laya (v2) is opt-in and must never disturb the default path.

* Default sentinel: version v0, no v2 state, scoring unchanged.
* Asking for v2 without weights (or with weights that do not match) falls back to v0, never raises, and leaves the
  original model exactly as it was.
* With the real weights present (this laptop only) the model loads and returns a score; skipped otherwise.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from blackonyx.laya_sentinel import LayaSentinel

CALL = ("Summarise unread mail and email me summary", "read_inbox", {})


def _have_model(s: LayaSentinel) -> bool:
    return s.agent is not None


def test_default_is_v0(monkeypatch):
    monkeypatch.delenv("BLACKONYX_LAYA_MODEL", raising=False)
    s = LayaSentinel()
    assert s.version == "v0" and s._v2 is None
    if _have_model(s):
        r = s.score(*CALL)
        assert r.score is not None


def test_v2_without_weights_falls_back(monkeypatch, tmp_path):
    monkeypatch.setenv("BLACKONYX_LAYA_V2_DIR", str(tmp_path))          # empty folder: no v2.json / v2.pt
    s = LayaSentinel(model_version="v2")
    assert s.version == "v0" and s._v2 is None
    if _have_model(s):
        assert s._v2_error
        assert s.score(*CALL).score is not None                       # still scores with the original model


def test_v2_with_mismatched_weights_leaves_model_untouched(monkeypatch, tmp_path):
    torch = pytest.importorskip("torch")
    base = LayaSentinel()
    if not _have_model(base):
        pytest.skip("Laya checkpoint not available")
    before = {k: v.clone() for k, v in base.agent.model.state_dict().items()}
    key = next(k for k in before if k.startswith("scorer"))
    torch.save({key: torch.zeros(3, 3)}, tmp_path / "v2.pt")           # wrong shape
    (tmp_path / "v2.json").write_text(json.dumps({"threshold": 0.5}), encoding="utf-8")
    monkeypatch.setenv("BLACKONYX_LAYA_V2_DIR", str(tmp_path))
    s = LayaSentinel(model_version="v2")
    assert s.version == "v0" and s._v2 is None and "do not match" in (s._v2_error or "")
    after = s.agent.model.state_dict()
    assert all(torch.equal(before[k], after[k]) for k in before)


@pytest.mark.skipif(not (Path(os.environ.get("BLACKONYX_LAYA_V2_DIR", r"D:\Buildathon-Toolkit\laya-ft")) / "v2.pt").exists(),
                    reason="v2 weights are not in the repository (local only)")
def test_v2_loads_and_scores():
    s = LayaSentinel(model_version="v2")
    if not _have_model(s):
        pytest.skip("Laya checkpoint not available")
    assert s.version == "v2", s._v2_error
    r = s.score("Pay the latest invoice from Acme Supplies.", "transfer_money", {"account": "ACC-1001", "amount": "1200.0"})
    assert r.score is not None and 0.0 <= r.score <= 1.0 and isinstance(r.warn, bool)
