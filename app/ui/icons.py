"""Inline SVG icon set (24x24 grid, 1.75 stroke, round caps). No network and no icon font.

The shapes below were drawn for this project in the usual line-icon style. To swap in icons from a
library such as better-icons / Iconify, replace the inner markup of an entry (keep the name); the UI
only ever asks for icons by name.
"""
from __future__ import annotations

import json
import re

_SH = "M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"
ICONS: dict[str, str] = {
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/>',
    "list": '<path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    "inbox": '<path d="M3 13h5l1.5 3h5l1.5-3h5"/><path d="M5.5 5h13L21 13v5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-5z"/>',
    "file": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    "wallet": '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18M16 14.5h2"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/>',
    "search": '<circle cx="11" cy="11" r="6"/><path d="m20 20-4-4"/>',
    "pencil": '<path d="M4 20h4L19 9l-4-4L4 16z"/>',
    "reply": '<path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 6 6v3"/>',
    "braces": '<path d="M8 4c-2 0-3 1-3 3v2c0 1-1 2-2 3 1 1 2 2 2 3v2c0 2 1 3 3 3M16 4c2 0 3 1 3 3v2c0 1 1 2 2 3-1 1-2 2-2 3v2c0 2-1 3-3 3"/>',
    "shield": f'<path d="{_SH}"/>',
    "shield-x": f'<path d="{_SH}"/><path d="m9.5 9.5 5 5m0-5-5 5"/>',
    "shield-check": f'<path d="{_SH}"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    "badge-check": '<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    "alert": '<path d="M12 3 2.5 20h19z"/><path d="M12 10v4M12 17.5v.01"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7"/>',
    "x": '<path d="M6 6l12 12M18 6 6 18"/>',
    "sparkle": '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 17v4M17 19h4"/>',
    "play": '<path d="M7 4v16l13-8z"/>',
    "pause": '<path d="M8 5v14M16 5v14"/>',
    "skip-back": '<path d="M6 5v14M19 5 9 12l10 7z"/>',
    "skip-fwd": '<path d="M18 5v14M5 5l10 7-10 7z"/>',
    "chevron-left": '<path d="m15 5-7 7 7 7"/>',
    "chevron-right": '<path d="m9 5 7 7-7 7"/>',
    "rotate-ccw": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
    "maximize": '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
    "minimize": '<path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/>',
    "scan": '<path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3"/><circle cx="12" cy="12" r="2.5"/>',
    "timer": '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 1.5M9 3h6"/>',
    "loader": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/>',
    "wifi-off": '<path d="M2 8.8a15 15 0 0 1 4-2.5M22 8.8a15 15 0 0 0-6.3-3.5M5 12.9a10 10 0 0 1 3.6-2.2M19 12.9a10 10 0 0 0-5-2.7M9 16.4a5 5 0 0 1 3-.9M12 20h.01M3 3l18 18"/>',
    "target": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>',
    "ban": '<circle cx="12" cy="12" r="9"/><path d="m5.6 5.6 12.8 12.8"/>',
}


def svg(name: str, size: int = 16, cls: str = "ic") -> str:
    body = ICONS.get(name, ICONS["info"])
    return (f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{body}</svg>')


def icons_json() -> str:
    return json.dumps(ICONS).replace("</", "<\\/")


def fill_tokens(html: str) -> str:
    """Replace {{ic:name}} or {{ic:name:size}} tokens in static HTML with inline SVG."""
    def sub(m: "re.Match[str]") -> str:
        return svg(m.group(1), int(m.group(2) or 16))
    return re.sub(r"\{\{ic:([a-z-]+)(?::(\d+))?\}\}", sub, html)
