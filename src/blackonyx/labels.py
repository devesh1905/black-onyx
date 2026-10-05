"""Origin sources (bitmask), trust levels and the join rule."""
from __future__ import annotations

import enum
from dataclasses import dataclass


class Source(enum.IntFlag):
    NONE = 0
    USER = 1
    CONTACTS = 2
    PAYEE_LIST = 4
    DOC_INDEX = 8
    EMAIL = 16
    WEB = 32
    FILE = 64
    TOOL_OTHER = 128


class Trust(enum.IntEnum):
    UNTRUSTED = 0
    VERIFIED = 1
    USER = 2


@dataclass(frozen=True)
class Label:
    sources: Source
    trust: Trust

    def source_names(self) -> list[str]:
        return [s.name for s in Source if s != Source.NONE and s in self.sources]

    def __str__(self) -> str:
        return f"{'|'.join(self.source_names()) or 'NONE'}/{self.trust.name}"


NEUTRAL = Label(Source.NONE, Trust.USER)  # identity of join: code constants carry no taint
USER_LABEL = Label(Source.USER, Trust.USER)


def join(*labels: Label) -> Label:
    """Sources = OR of inputs, trust = lowest input trust."""
    sources = Source.NONE
    trust = Trust.USER
    for lb in labels:
        sources |= lb.sources
        trust = min(trust, lb.trust)
    return Label(sources, trust)
