"""Phone push notifications for long jobs (ntfy). Standard library only, so it works in the GPU venv too.

    from notify import notify            # when the script lives in eval/ and is run as a file
    notify("Laya training", "seed 7 done: dev 99.5%, test 91.8%")

Topic: env BLACKONYX_PROGRESS_TOPIC (default build_thon). Never raises; a failed push is ignored. Sends only what you pass, so keep
messages to numbers and names (no data). Do not spam: one push per step, seed, 20% of a job, or error.
"""
from __future__ import annotations

import os
import threading
import urllib.request

TOPIC = os.environ.get("BLACKONYX_PROGRESS_TOPIC", "build_thon")


def notify(title: str, message: str = "", topic: str = TOPIC, wait: bool = False) -> None:
    def _go() -> None:
        try:
            req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=message.encode("utf-8"), method="POST",
                                         headers={"Title": title.encode("ascii", "replace").decode()})
            urllib.request.urlopen(req, timeout=5).close()
        except Exception:
            pass
    t = threading.Thread(target=_go, daemon=True)
    t.start()
    if wait:
        t.join(6)
