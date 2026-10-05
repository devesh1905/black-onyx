"""Deterministic extractor and transforms. Output labels are inherited from the inputs."""
from __future__ import annotations

import base64
import re
from typing import Any

from .labeled import LabeledObject, derive, ljoin, lfmt, raw

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def extract_email(lo: LabeledObject, pick: str = "first") -> LabeledObject:
    found = EMAIL_RE.findall(str(raw(lo)))
    v = (found[0] if pick == "first" else found[-1]) if found else ""
    return derive(v, "extract_email", lo)


def extract_account(lo: LabeledObject) -> LabeledObject:
    found = re.findall(r"ACC-\d{3,}", str(raw(lo)))
    return derive(found[-1] if found else "", "extract_account", lo)


def extract_amount(lo: LabeledObject) -> LabeledObject:
    found = re.findall(r"amount[^\d\n]{0,25}\$?([\d,]+(?:\.\d+)?)", str(raw(lo)), flags=re.I)
    return derive(float(found[-1].replace(",", "")) if found else 0.0, "extract_amount", lo)


def extract_vendor(lo: LabeledObject) -> LabeledObject:
    m = re.search(r"Vendor:\s*(.+)", str(raw(lo)))
    return derive(m.group(1).strip() if m else "", "extract_vendor", lo)


def extract_time(lo: LabeledObject) -> LabeledObject:
    m = re.search(r"[Pp]roposed time:\s*([^.\n]+)", str(raw(lo)))
    return derive(m.group(1).strip() if m else "", "extract_time", lo)


def decode_b64(lo: LabeledObject) -> LabeledObject:
    try:
        v = base64.b64decode(str(raw(lo)).strip()).decode("utf-8", "replace")
    except Exception:
        v = ""
    return derive(v, "decode_b64", lo)


def select_email(emails: LabeledObject, keyword: str = "", pick: str = "latest") -> LabeledObject:
    """Email whose subject contains keyword: the latest (default) or the first."""
    cands = [e for e in emails if keyword.lower() in str(raw(e["subject"])).lower()]
    if not cands:
        return derive({}, "select_email", emails)
    return cands[0] if pick == "first" else cands[-1]  # inbox is in id order


def first_sentence(lo: LabeledObject) -> LabeledObject:
    s = str(raw(lo)).strip().replace("\n", " ")
    m = re.split(r"(?<=[.!?])\s", s, maxsplit=1)
    return derive(m[0], "first_sentence", lo)


def summarize(emails: LabeledObject) -> LabeledObject:
    """One line per email; the summary inherits the labels of every email."""
    lines = [lfmt("- {subject}: {first}", subject=e["subject"], first=first_sentence(e["body"])) for e in emails]
    return derive("\n".join(str(raw(x)) for x in lines), "summarize", emails, *lines)


def field(lo: LabeledObject, key: str) -> LabeledObject:
    return lo[key]


def concat_docs(docs: list[LabeledObject]) -> LabeledObject:
    return ljoin("\n---\n", docs)


TRANSFORMS: dict[str, Any] = {
    "extract_email": extract_email, "extract_account": extract_account, "extract_amount": extract_amount,
    "extract_vendor": extract_vendor, "extract_time": extract_time, "decode_b64": decode_b64,
    "select_email": select_email, "field": field, "concat_docs": concat_docs, "summarize": summarize, "first_sentence": first_sentence,
}
