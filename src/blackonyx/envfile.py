"""Tiny .env loader (no dependency). Looks OUTSIDE the repo so keys never get committed.

Order: $BLACKONYX_ENV, then <repo parent>/.env. Existing environment variables win; blank values are ignored.
"""
from __future__ import annotations

import os
from pathlib import Path


def env_path() -> Path:
    return Path(os.environ.get("BLACKONYX_ENV") or Path(__file__).resolve().parents[3] / ".env")


def load_env() -> list[str]:
    p = env_path()
    loaded: list[str] = []
    if not p.is_file():
        return loaded
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v and k not in os.environ:
            os.environ[k] = v
            loaded.append(k)
    return loaded
