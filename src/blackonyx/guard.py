"""Drop-in guard for a REAL tool-calling loop (any LLM client).

Black Onyx's engine labels values exactly because it runs the plan itself. A real LLM agent hands you
plain strings (a tool name and its arguments), so provenance has to be recovered at the boundary. This adapter
does that conservatively ("taint by origin of the text"):

  * an argument that appears in the user's request            -> USER
  * an argument that is an entry of a trusted table (contacts) -> VERIFIED, source of that table
  * an argument that appears in earlier tool output            -> UNTRUSTED, source of that tool result
  * anything else (the model invented it)                      -> UNTRUSTED

Every call is then checked with the same YAML policy as the engine. Allowed calls run, denied calls return a
refusal the model can read, and every decision is written to the audit log.

    guard = Guard(user_request="Summarise my mail and email me the summary",
                  trusted={Source.CONTACTS: {"me@corp.com", "priya@corp.com"}})
    guard.register("read_inbox", read_inbox, result_source=Source.EMAIL)
    guard.register("send_email", send_email)
    # inside your agent loop, instead of calling the tool directly:
    out = guard.call("send_email", to="x@evil.co", subject="hi", body="...")   # -> GuardResult(allowed=False, ...)

Limits (be honest about them): substring matching can be fooled by a model that rewrites a value (for example
re-spelling an address), which is why the conservative default for unknown values is UNTRUSTED. The engine's
LabeledObject path remains the stronger mechanism; this adapter is the pragmatic bridge for existing agents.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Optional

from . import audit as _audit
from .labeled import LabeledObject
from .labels import Label, Source, Trust
from .policy import Policy


def _in_request(needle: str, hay: str) -> bool:
    """True if `needle` appears in `hay` as a whole token. Plain substring matching would let a truncated address
    ('priya@corp.co' inside 'priya@corp.com') inherit the user's trust, so the match must end at a token boundary."""
    if not needle:
        return False
    pat = r"(?<![\w@.+-])" + re.escape(needle) + r"(?![\w@-])(?!\.\w)"
    return re.search(pat, hay, re.I) is not None


@dataclass
class GuardResult:
    allowed: bool
    tool: str
    output: Any = None
    reason: str = ""
    decisions: list[dict[str, Any]] = field(default_factory=list)

    def for_model(self) -> str:
        """What to feed back to the model."""
        if self.allowed:
            return str(self.output)
        return f"[blocked by Black Onyx] {self.reason}"


class Guard:
    def __init__(self, user_request: str = "", policy: Optional[Policy] = None,
                 trusted: Optional[Mapping[Source, Iterable[str]]] = None,
                 audit: Optional[_audit.Audit] = None, min_match_len: int = 3):
        self.request = user_request
        self.policy = policy or Policy.load()
        self.trusted = {src: {str(v).lower() for v in vals} for src, vals in (trusted or {}).items()}
        self.audit = audit
        self.min_len = min_match_len
        self.tools: dict[str, tuple[Callable[..., Any], Source]] = {}
        self.observations: list[tuple[Source, str]] = []   # untrusted text the model has seen
        self.decisions: list[GuardResult] = []

    # ---- registration -------------------------------------------------------------------
    def register(self, name: str, fn: Callable[..., Any], result_source: Source = Source.TOOL_OTHER) -> None:
        self.tools[name] = (fn, result_source)

    def tool(self, name: Optional[str] = None, result_source: Source = Source.TOOL_OTHER):
        def deco(fn):
            self.register(name or fn.__name__, fn, result_source)
            return fn
        return deco

    def observe(self, source: Source, text: Any) -> None:
        """Record untrusted text the model has seen (tool results are recorded automatically)."""
        self.observations.append((source, str(text)))

    # ---- provenance of one argument value --------------------------------------------------
    def label_value(self, value: Any) -> Label:
        s = str(value).strip()
        low = s.lower()
        if _in_request(s, self.request):
            return Label(Source.USER, Trust.USER)
        for src, vals in self.trusted.items():
            if low in vals:
                return Label(src, Trust.VERIFIED)
        for src, text in self.observations:
            if len(low) >= self.min_len and low in text.lower():
                return Label(src, Trust.UNTRUSTED)
        return Label(Source.TOOL_OTHER, Trust.UNTRUSTED)   # unknown origin: the model produced it

    # ---- the guarded call -------------------------------------------------------------------
    def call(self, name: str, **args: Any) -> GuardResult:
        a = self.audit or _audit.active()
        if name not in self.tools:
            return self._finish(GuardResult(False, name, reason=f"tool '{name}' is not registered"), a, None)
        decisions: list[dict[str, Any]] = []
        denied: Optional[dict[str, Any]] = None
        for k, v in args.items():
            lb = self.label_value(v)
            lo = LabeledObject(v, lb, name=f"{name}.{k}")
            d = self.policy.check(name, k, lo)
            rec = {"argument": k, "value": str(v)[:80], "decision": "allow" if d.allow else "deny", "reason": d.reason,
                   "sources": lb.source_names(), "trust": lb.trust.name}
            decisions.append(rec)
            if a is not None:
                a.emit("call_check", call_id=f"g{len(self.decisions) + 1}", tool=name, argument=k, value_id=lo.vid,
                       decision=rec["decision"], reason=d.reason, sources=rec["sources"], trust=rec["trust"])
            if not d.allow and denied is None:
                denied = rec
        if denied is not None:
            reason = (f"{name}.{denied['argument']} came from {', '.join(denied['sources'])} ({denied['trust']}): "
                      f"{denied['reason']}")
            return self._finish(GuardResult(False, name, reason=reason, decisions=decisions), a, denied)
        fn, src = self.tools[name]
        out = fn(**args)
        self.observe(src, out)           # what a tool returned is untrusted text the model will now read
        return self._finish(GuardResult(True, name, output=out, decisions=decisions), a, None)

    def _finish(self, res: GuardResult, a: Optional[_audit.Audit], denied: Optional[dict[str, Any]]) -> GuardResult:
        self.decisions.append(res)
        if a is not None and not res.allowed:
            a.emit("alert", call_id=f"g{len(self.decisions)}", tool=res.tool, reason=res.reason,
                   chain=f"{denied['argument']} <- {', '.join(denied['sources'])}, {denied['trust']}" if denied else res.tool)
        return res
