"""Append-only event log (JSONL) plus provenance bookkeeping for alert chains."""
from __future__ import annotations

import contextvars
import json
import time
from pathlib import Path
from typing import Any, Optional

ACTIVE: contextvars.ContextVar[Optional["Audit"]] = contextvars.ContextVar("blackonyx_audit", default=None)


class Audit:
    def __init__(self, path: Optional[str | Path] = None):
        self.events: list[dict[str, Any]] = []
        self.t0 = time.perf_counter()
        self.seq = 0
        self.vcount = 0
        self.parents: dict[str, tuple[str, list[str]]] = {}
        self.names: dict[str, str] = {}
        self.labels: dict[str, Any] = {}
        self._fh = open(path, "w", encoding="utf-8") if path else None
        self._token = None

    def __enter__(self) -> "Audit":
        self._token = ACTIVE.set(self)
        return self

    def __exit__(self, *a) -> None:
        ACTIVE.reset(self._token)
        self.close()

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None

    def emit(self, type: str, **fields: Any) -> dict[str, Any]:
        self.seq += 1
        ev = {"seq": self.seq, "ts": round(time.perf_counter() - self.t0, 4), "type": type, **fields}
        self.events.append(ev)
        if self._fh:
            self._fh.write(json.dumps(ev) + "\n")
            self._fh.flush()
        return ev

    def new_vid(self) -> str:
        self.vcount += 1
        return f"v{self.vcount}"

    def register(self, vid: str, label, name: Optional[str], op: Optional[str], inputs: list[str]) -> None:
        self.labels[vid] = label
        if name:
            self.names[vid] = name
        if op:
            self.parents[vid] = (op, inputs)

    def chain(self, vid: str, depth: int = 0) -> str:
        """Readable provenance, e.g. concat(email#7, email#9)."""
        if vid in self.parents and depth < 6:
            op, ins = self.parents[vid]
            if op in ("index", "slice", "extract_sentence", "split") and ins:
                return self.chain(ins[-1], depth + 1)  # structural noise: show the underlying value
            return f"{op}({', '.join(self.chain(i, depth + 1) for i in ins)})"
        return self.names.get(vid, vid)


def active() -> Optional[Audit]:
    return ACTIVE.get()
