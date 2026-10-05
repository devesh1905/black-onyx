"""Black Onyx UI components (self-contained HTML, no CDN, works offline)."""
from __future__ import annotations

import json
from pathlib import Path

from .icons import fill_tokens, icons_json
from typing import Any, Optional

_HERE = Path(__file__).resolve().parent
DEFENCE_NAMES = {"D0": "undefended", "D1": "keyword filter", "D2": "Black Onyx rules", "D3": "rules + Laya",
                 "D4": "Laya alone"}


def _json(obj: Any) -> str:
    # keep the JSON safe inside a <script> block
    return json.dumps(obj, default=str).replace("</", "<\\/").replace("<!--", "<\\!--")


def render_stage(events: list[dict[str, Any]], autoplay: bool = True, defence: Optional[str] = None) -> str:
    """The animated split view: monitor feed, provenance graph, scoreboard, replay controls."""
    html = (_HERE / "stage.html").read_text(encoding="utf-8")
    d = defence or (events[0].get("defence") if events else None)
    opt = {"autoplay": autoplay, "defence": d, "defenceName": DEFENCE_NAMES.get(d or "", "")}
    html = fill_tokens(html)
    return (html.replace("/*__EVENTS__*/[]", _json(events)).replace("/*__OPT__*/{}", _json(opt))
            .replace("/*__ICONS__*/{}", icons_json()))
