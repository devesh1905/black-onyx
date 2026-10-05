"""Validated declassifiers: the only way trust goes up.

Each is small and deterministic, returns data from a trusted table (never the untrusted
input itself, except amount_check which only validates a bound), and logs one event.
"""
from __future__ import annotations

from typing import Any

from . import audit as _audit
from .labeled import LabeledObject, label_of, raw
from .labels import Label, Source, Trust, join


class DeclassifyError(Exception):
    pass


def _norm(x: Any) -> str:
    return str(raw(x)).strip().lower()


def _log(validator: str, inp: LabeledObject, out: LabeledObject | None, rule: str, ok: bool) -> None:
    a = _audit.active()
    if a is None:
        return
    shown = out if out is not None else inp
    a.emit("declassify", validator=validator, input=inp.vid, output=shown.vid, rule=rule, ok=ok,
           sources=shown.label.source_names(), trust=shown.label.trust.name,
           preview=str(raw(shown))[:80])


def _verified(value: Any, source: Source, inp: LabeledObject, op: str) -> LabeledObject:
    out = LabeledObject(value, Label(source, Trust.VERIFIED), op=op, inputs=[inp], emit=False)
    return out


def payee_lookup(vendor: LabeledObject, user_vendor: LabeledObject, world) -> LabeledObject:
    """Account for a vendor from the internal payee list. The vendor on the invoice must
    equal the vendor the user named."""
    rule = "vendor on invoice == vendor named by user, and vendor is in payee list"
    v = _norm(vendor)
    if v != _norm(user_vendor) or v not in world.payees:
        _log("payee_lookup", vendor, None, f"REJECTED: {rule}", False)
        raise DeclassifyError(f"vendor '{raw(vendor)}' not accepted")
    out = _verified(world.payees[v], Source.PAYEE_LIST, vendor, "payee_lookup")
    _log("payee_lookup", vendor, out, rule, True)
    return out


def contact_lookup(key: LabeledObject, world) -> LabeledObject:
    """Address for a person's name, or confirmation that an address is in the contacts list."""
    rule = "name or address matches a contacts entry"
    k = _norm(key)
    hit = world.contacts.get(k)
    if hit is None:
        for name, addr in world.contacts.items():
            if k == addr or k in name or name in k:
                hit = addr
                break
    if hit is None:
        _log("contact_lookup", key, None, f"REJECTED: {rule}", False)
        raise DeclassifyError(f"'{raw(key)}' is not in contacts")
    out = _verified(hit, Source.CONTACTS, key, "contact_lookup")
    _log("contact_lookup", key, out, rule, True)
    return out


def doc_resolve(words: LabeledObject, world) -> LabeledObject:
    """Path from the user's OWN search words via the internal doc index."""
    rule = "search words came from the user, and match the doc index"
    k = _norm(words)
    if label_of(words).trust != Trust.USER or not any(kw in k for kw in world.doc_index):
        _log("doc_resolve", words, None, f"REJECTED: {rule}", False)
        raise DeclassifyError("words not accepted")
    path = next(p for kw, p in world.doc_index.items() if kw in k)
    out = _verified(path, Source.DOC_INDEX, words, "doc_resolve")
    _log("doc_resolve", words, out, rule, True)
    return out


def amount_check(amount: LabeledObject, user_vendor: LabeledObject, world) -> LabeledObject:
    """Accept an amount only if it does not exceed the ledger total for that payee."""
    rule = "0 < amount <= ledger total for the vendor the user named"
    cap = world.ledger.get(_norm(user_vendor))
    val = raw(amount)
    if cap is None or not (0 < val <= cap):
        _log("amount_check", amount, None, f"REJECTED: {rule}", False)
        raise DeclassifyError(f"amount {val} not accepted")
    out = _verified(val, Source.PAYEE_LIST, amount, "amount_check")
    _log("amount_check", amount, out, rule, True)
    return out


def mailbox_ref(msg_id: LabeledObject, world) -> LabeledObject:
    """A message id is accepted only if it exists in the real mailbox (the mailbox is the table)."""
    rule = "message id exists in the mailbox"
    if raw(msg_id) not in {m["id"] for m in world.inbox}:
        _log("mailbox_ref", msg_id, None, f"REJECTED: {rule}", False)
        raise DeclassifyError("unknown message id")
    out = _verified(raw(msg_id), Source.TOOL_OTHER, msg_id, "mailbox_ref")
    _log("mailbox_ref", msg_id, out, rule, True)
    return out


VALIDATORS = {"mailbox_ref": mailbox_ref, "payee_lookup": payee_lookup, "contact_lookup": contact_lookup, "doc_resolve": doc_resolve,
              "amount_check": amount_check}
