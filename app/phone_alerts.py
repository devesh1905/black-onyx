"""Optional phone alerts: push a short message to an ntfy topic whenever Black Onyx blocks a call.

Off the critical path: runs in a background thread, 3 s timeout, silent on failure (offline demos are unaffected).
Only the tool name and the policy reason are sent, never message bodies, addresses or file contents.
"""
from __future__ import annotations

import os
import threading
import urllib.request
from typing import Any, Iterable

TOPIC = os.environ.get("BLACKONYX_NTFY_TOPIC", "black_onyx")
MAX_PER_RUN = 3


def _post(title: str, body: str, topic: str) -> None:
    try:
        req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"), method="POST",
                                     headers={"Title": title, "Priority": "high", "Tags": "shield,rotating_light"})
        urllib.request.urlopen(req, timeout=3).close()
    except Exception:
        pass


def alert_messages(events: Iterable[dict[str, Any]]) -> list[tuple[str, str]]:
    out = []
    for e in events:
        if e.get("type") == "alert":
            tool = str(e.get("tool", "a tool"))
            reason = str(e.get("reason", "policy violation")).split("\n")[0][:140]
            out.append(("Black Onyx blocked an attack", f"Blocked {tool}: {reason}"))
    return out[:MAX_PER_RUN]


def send_block_alerts(events: Iterable[dict[str, Any]], topic: str = TOPIC) -> int:
    msgs = alert_messages(events)
    for title, body in msgs:
        threading.Thread(target=_post, args=(title, body, topic), daemon=True).start()
    return len(msgs)
