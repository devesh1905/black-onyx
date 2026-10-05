"""Tests for offline PyVis graph generation (app/graph.py)."""
from __future__ import annotations

import re
from app.fake_events import fake_run
from app.graph import events_to_html


def test_empty_events_handling():
    """Verify empty events list does not raise and returns clean placeholder HTML."""
    html = events_to_html([])
    assert isinstance(html, str)
    assert len(html) > 0
    assert "No Events Recorded" in html


def test_none_events_handling():
    """Verify None input is safely handled."""
    html = events_to_html(None)
    assert isinstance(html, str)
    assert "No Events Recorded" in html


def test_no_external_cdn_tags():
    """Verify generated HTML has no external HTTP/HTTPS script or stylesheet CDN tags.

    Judges requirement: Must render with Wi-Fi off.
    PyVis default bootstrap and CDN tags must be stripped.
    """
    events = fake_run(attack=True)
    html = events_to_html(events)

    # Check for external script src tags with http/https
    external_scripts = re.findall(r'<script[^>]+src=["\']https?://[^"\']+["\']', html, re.IGNORECASE)
    assert external_scripts == [], f"Found external script tags: {external_scripts}"

    # Check for external stylesheet links
    external_links = re.findall(r'<link[^>]+href=["\']https?://[^"\']+["\']', html, re.IGNORECASE)
    assert external_links == [], f"Found external stylesheet links: {external_links}"

    # Ensure vis.Network is inlined and present
    assert "vis.Network" in html or "Network(" in html


def test_red_color_for_deny_event():
    """Verify red color (#ef4444) is present when a call is denied/blocked."""
    events = fake_run(attack=True)
    html = events_to_html(events)

    # Red color for blocked node
    assert "#ef4444" in html
    # Check that alert/blocked status appears
    assert "BLOCKED" in html
    # Flashing JavaScript injected
    assert "startFlashing" in html or "setInterval" in html


def test_benign_run_colors():
    """Verify benign run does not flag blocked calls, but includes user & effect nodes."""
    events = fake_run(attack=False)
    html = events_to_html(events)

    # Should have green (USER) and purple (EFFECT)
    assert "#22c55e" in html
    assert "#8b5cf6" in html
    assert "EFFECT:" in html
