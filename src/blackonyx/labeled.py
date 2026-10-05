"""LabeledObject: a value plus its provenance label, propagated by operator overloading.

Strict mode (default on): str(), f-strings, format() and % raise, because they would
return a plain string and silently drop the label. Use lfmt/ljoin, or reveal() at sinks.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Optional

from . import audit as _audit
from .labels import NEUTRAL, USER_LABEL, Label, Source, Trust, join

STRICT = True
REVEAL_LOG: list[tuple[str, str]] = []


class StrictModeError(TypeError):
    pass


def set_strict(flag: bool) -> None:
    global STRICT
    STRICT = flag


def raw(x: Any) -> Any:
    return x.value if isinstance(x, LabeledObject) else x


def label_of(x: Any) -> Label:
    return x.label if isinstance(x, LabeledObject) else NEUTRAL


QUIET_OPS = {"index", "slice", "extract_sentence", "split", "first_sentence", "fmt"}


def _preview(v: Any) -> str:
    if isinstance(v, list):
        return f"[{len(v)} items]"
    if isinstance(v, dict):
        return "{" + ", ".join(v) + "}"
    return re.sub(r"\s+", " ", v if isinstance(v, str) else repr(v))[:80]


class LabeledObject:
    __slots__ = ("value", "label", "vid", "name")

    def __init__(self, value: Any, label: Label, name: Optional[str] = None,
                 op: Optional[str] = None, inputs: Iterable["LabeledObject"] = (), emit: bool = True):
        self.value = value
        self.label = label
        self.name = name
        self.vid = None
        a = _audit.active()
        if a is not None:
            self.vid = a.new_vid()
            in_ids = [i.vid for i in inputs if isinstance(i, LabeledObject) and i.vid]
            a.register(self.vid, label, name, op, in_ids)
            if op and emit and op not in QUIET_OPS:
                a.emit("op", op=op, inputs=in_ids, output=self.vid, sources=label.source_names(),
                       trust=label.trust.name, preview=_preview(value))

    def _derive(self, value: Any, op: str, *others: Any) -> "LabeledObject":
        ins = [self] + [o for o in others if isinstance(o, LabeledObject)]
        return LabeledObject(value, join(*[label_of(i) for i in ins]), op=op, inputs=ins)

    # ---- strict-mode guards ---------------------------------------------------
    def __str__(self) -> str:
        if STRICT:
            raise StrictModeError("str() would drop the label; use reveal() or lfmt()")
        return str(self.value)

    def __format__(self, spec: str) -> str:
        if STRICT:
            raise StrictModeError("f-string/format() would drop the label; use lfmt()")
        return format(self.value, spec)

    def __mod__(self, other):
        if STRICT:
            raise StrictModeError("% formatting would drop the label; use lfmt()")
        return NotImplemented

    def __int__(self):
        if STRICT:
            raise StrictModeError("int() would drop the label")
        return int(self.value)

    def __float__(self):
        if STRICT:
            raise StrictModeError("float() would drop the label")
        return float(self.value)

    def __repr__(self) -> str:
        return f"LO({_preview(self.value)!r} | {self.label})"

    def reveal(self, why: str = "") -> Any:
        """Explicit, logged escape hatch for sinks and the UI."""
        REVEAL_LOG.append((self.vid or "-", why))
        return self.value

    # ---- operators ------------------------------------------------------------
    def __add__(self, other):
        return self._derive(self.value + raw(other), "concat", other)

    def __radd__(self, other):
        return self._derive(raw(other) + self.value, "concat")

    def __sub__(self, other):
        return self._derive(self.value - raw(other), "sub", other)

    def __rsub__(self, other):
        return self._derive(raw(other) - self.value, "sub")

    def __mul__(self, other):
        return self._derive(self.value * raw(other), "mul", other)

    __rmul__ = __mul__

    def __truediv__(self, other):
        return self._derive(self.value / raw(other), "div", other)

    def __getitem__(self, key):
        k = raw(key)
        item = self.value[k]
        if isinstance(item, LabeledObject):
            return LabeledObject(item.value, join(self.label, item.label, label_of(key)), name=item.name,
                                 op="index", inputs=[self, item])
        return self._derive(item, "slice" if isinstance(k, slice) else "index", key)

    def __iter__(self):
        if isinstance(self.value, dict):
            yield from self.value
        else:
            for i in range(len(self.value)):
                yield self[i]

    def __len__(self) -> int:
        return len(self.value)

    def __bool__(self) -> bool:
        return bool(self.value)

    def __contains__(self, item) -> bool:
        return raw(item) in self.value

    def __eq__(self, other) -> bool:
        return self.value == raw(other)

    def __ne__(self, other) -> bool:
        return self.value != raw(other)

    def __lt__(self, other) -> bool:
        return self.value < raw(other)

    def __le__(self, other) -> bool:
        return self.value <= raw(other)

    def __gt__(self, other) -> bool:
        return self.value > raw(other)

    def __ge__(self, other) -> bool:
        return self.value >= raw(other)

    def __hash__(self) -> int:
        return hash(str(self.value))

    # ---- str / dict / list methods that keep the label ------------------------
    def split(self, sep=None, maxsplit=-1) -> "LabeledObject":
        parts = [LabeledObject(p, self.label, name=self.name, op="split", inputs=[self], emit=False)
                 for p in self.value.split(raw(sep), maxsplit)]
        return LabeledObject(parts, self.label, op="split", inputs=[self, sep])

    def splitlines(self) -> "LabeledObject":
        return self.split("\n")

    def strip(self, chars=None):
        return self._derive(self.value.strip(raw(chars)), "strip")

    def lower(self):
        return self._derive(self.value.lower(), "lower")

    def upper(self):
        return self._derive(self.value.upper(), "upper")

    def replace(self, a, b):
        return self._derive(self.value.replace(raw(a), raw(b)), "replace", a, b)

    def join(self, items) -> "LabeledObject":
        return ljoin(self, items)

    def startswith(self, p) -> bool:
        return self.value.startswith(raw(p))

    def endswith(self, p) -> bool:
        return self.value.endswith(raw(p))

    def get(self, key, default=None):
        if raw(key) in self.value:
            return self[key]
        return default

    def values(self):
        return [self[k] for k in self.value]

    def items(self):
        return [(k, self[k]) for k in self.value]


# ---- constructors and labeled helpers -------------------------------------------
def lit(value: Any, name: Optional[str] = None) -> LabeledObject:
    """A value typed by the user (or fixed by the user's plan): USER trust."""
    return LabeledObject(value, USER_LABEL, name=name or "user")


def source_obj(value: Any, source: Source, name: str, trust: Trust = Trust.UNTRUSTED) -> LabeledObject:
    return LabeledObject(value, Label(source, trust), name=name)


def lolist(items: list, name: Optional[str] = None) -> LabeledObject:
    return LabeledObject(list(items), join(*[label_of(i) for i in items]), name=name)


def lodict(d: dict, name: Optional[str] = None) -> LabeledObject:
    return LabeledObject(dict(d), join(*[label_of(v) for v in d.values()]), name=name)


def ljoin(sep, items) -> LabeledObject:
    items = list(items.value) if isinstance(items, LabeledObject) else list(items)
    ins = [i for i in items if isinstance(i, LabeledObject)]
    if isinstance(sep, LabeledObject):
        ins.append(sep)
    value = raw(sep).join(str(raw(i)) for i in items)
    return LabeledObject(value, join(*[label_of(i) for i in ins]), op="join", inputs=ins)


def lfmt(template: str, **kw: Any) -> LabeledObject:
    """Labeled str.format: {key} placeholders; the template itself carries no taint."""
    ins = [v for v in kw.values() if isinstance(v, LabeledObject)]
    value = re.sub(r"\{(\w+)\}", lambda m: str(raw(kw[m.group(1)])), template)
    return LabeledObject(value, join(*[label_of(i) for i in ins]), op="fmt", inputs=ins)


def derive(value: Any, op: str, *inputs: Any, name: Optional[str] = None) -> LabeledObject:
    ins = [i for i in inputs if isinstance(i, LabeledObject)]
    return LabeledObject(value, join(*[label_of(i) for i in ins]), name=name, op=op, inputs=ins)
