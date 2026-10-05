import os

from app.ui.splash import custom_emblem, splash_html


def test_default_splash_is_self_contained_and_reduced_motion_safe(tmp_path, monkeypatch):
    monkeypatch.setattr("app.ui.splash.BRAND_DIR", tmp_path)  # ignore any local override files
    monkeypatch.delenv("BLACKONYX_EMBLEM", raising=False)
    h = splash_html()
    assert "Trust every action. Verify every source." in h and "prefers-reduced-motion" in h
    assert "http://" not in h.replace("http://www.w3.org", "") and "https://" not in h


def test_override_slot_uses_user_image(tmp_path, monkeypatch):
    from PIL import Image
    p = tmp_path / "mine.png"
    Image.new("RGBA", (40, 20), (255, 255, 255, 255)).save(p)
    monkeypatch.setattr("app.ui.splash.BRAND_DIR", tmp_path / "none")
    monkeypatch.setenv("BLACKONYX_EMBLEM", str(p))
    assert custom_emblem().startswith("data:image/png;base64,")
    h = splash_html()
    assert "class='bo-img'" in h and "bo-stack bo-word" not in h


def test_home_logo_slot_is_separate(tmp_path, monkeypatch):
    from PIL import Image
    from app.ui.splash import custom_logo
    p = tmp_path / "sq.png"
    Image.new("RGBA", (64, 64), (255, 255, 255, 255)).save(p)
    monkeypatch.setattr("app.ui.splash.BRAND_DIR", tmp_path / "none")
    monkeypatch.setenv("BLACKONYX_LOGO", str(p))
    assert custom_logo().startswith("data:image/png")
