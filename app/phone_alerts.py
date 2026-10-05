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


WHAT = {
    "read_file": "read a file the user never asked for",
    "send_email": "send mail to an address the user never named",
    "reply_email": "send a reply the user never asked for",
    "transfer_money": "move money to an account the user never named",
    "http_get": "call out to a URL the user never named",
    "fetch_url": "call out to a URL the user never named",
    "calendar_add": "add a calendar event the user never asked for",
    "write_file": "write a file the user never asked for",
}


def alert_messages(events: Iterable[dict[str, Any]]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for e in events:
        if e.get("type") != "alert":
            continue
        tool = str(e.get("tool", "a tool"))
        origin = str(e.get("chain", "")).rsplit("<-", 1)[-1].strip().lower().replace(",", "")
        what = WHAT.get(tool, f"call {tool} outside the plan")
        msg = (f"Injected text tried to make the agent {what}. Blocked"
               + (f" ({origin})." if origin else "."))
        item = (f"Black Onyx blocked {tool}", msg)
        if item not in out:
            out.append(item)
    return out[:MAX_PER_RUN]


def send_block_alerts(events: Iterable[dict[str, Any]], topic: str = TOPIC) -> int:
    msgs = alert_messages(events)
    for title, body in msgs:
        threading.Thread(target=_post, args=(title, body, topic), daemon=True).start()
    return len(msgs)
