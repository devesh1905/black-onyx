"""Sentinel interface (contract between engine and Laya integration).

The sentinel is advisory: it scores whether a tool call fits the user's task.
It never overrides a policy decision. Implementations must never raise; on any
failure they return SentinelResult(score=None, ...).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Mapping, Optional, Protocol


@dataclass
class SentinelResult:
    score: Optional[float]  # P(call fits task) in [0,1]; None = no opinion
    ms: float = 0.0         # time spent scoring
    warn: Optional[bool] = None  # True if score is below the calibrated threshold


class Sentinel(Protocol):
    def score(self, task: str, tool: str, args: Mapping[str, str]) -> SentinelResult: ...


class NullSentinel:
    """No opinion. Used in D0-D2 and as the fallback when Laya fails."""

    def score(self, task: str, tool: str, args: Mapping[str, str]) -> SentinelResult:
        t = time.perf_counter()
        return SentinelResult(score=None, ms=(time.perf_counter() - t) * 1000, warn=None)
