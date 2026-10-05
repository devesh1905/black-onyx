"""Interpreter: runs a fixed plan, wraps every tool I/O in labels, gates every call.

Defences:
  D0 undefended (follows instructions found in tool output)
  D1 D0 + keyword filter on tool output
  D2 Black Onyx rules (labels, policy gate, validators, out-of-plan guard)
  D3 D2 + Laya sentinel (advisory)
  D4 sentinel alone decides (ablation)
"""
from __future__ import annotations

import time
from typing import Any, Optional

from . import audit as _audit
from .agent import filter_value, parse_directives
from .extractor import TRANSFORMS
from .labeled import (LabeledObject, derive, label_of, lit, lodict, lolist, raw, source_obj)
from .labels import Label, Source, Trust, join
from .plan import Plan, Ref, Step
from .policy import Decision, Policy
from .sentinel import NullSentinel, Sentinel
from .validators import VALIDATORS, DeclassifyError
from .world import World

ENFORCING = {"D2", "D3"}
TEXT_TOOLS = {"read_inbox", "read_file", "web_fetch", "search_docs"}


class Interpreter:
    def __init__(self, world: World, defence: str = "D2", policy: Optional[Policy] = None,
                 sentinel: Optional[Sentinel] = None, audit: Optional[_audit.Audit] = None,
                 plan_guard: bool = True, use_labelstore: bool = True, follow_injections: bool = True):
        self.world = world
        self.defence = defence
        self.enforce = defence in ENFORCING
        self.policy = policy or Policy.load()
        self.sentinel = sentinel or NullSentinel()
        self.audit = audit or _audit.active()
        self.plan_guard = plan_guard
        self.use_labelstore = use_labelstore
        self.follow = follow_injections
        self.env: dict[str, Any] = {}
        self.planned_ids: set[str] = set()
        self.gate_ms: list[float] = []
        self.laya_ms: list[float] = []
        self.denied: list[dict] = []
        self.laya_warns: list[dict] = []
        self.legit_sensitive = 0
        self.legit_denied = 0
        self.alerts = 0
        self._xn = 0
        self.request = ""

    # ---- helpers ------------------------------------------------------------------
    def emit(self, type: str, **f: Any) -> None:
        self.audit.emit(type, **f)

    def _resolve(self, v: Any, plain_literal: bool = False) -> Any:
        if isinstance(v, Ref):
            return self.env.get(v.name)
        if isinstance(v, list):
            return [self._resolve(x, plain_literal) for x in v]
        if isinstance(v, LabeledObject) or plain_literal:
            return v
        return lit(v)

    # ---- running a plan -----------------------------------------------------------
    def run(self, plan: Plan) -> None:
        self.request = plan.request
        self.emit("request", text=plan.request, defence=self.defence, task_id=plan.task_id)
        self.emit("plan", steps=[{"call_id": s.call_id, "tool": s.tool, "desc": s.desc} for s in plan.calls()])
        self.planned_ids = {s.call_id for s in plan.calls()}
        for step in plan.steps:
            try:
                self._step(step)
            except _Skip:
                continue

    def _step(self, s: Step) -> None:
        if s.kind == "xform":
            args = [self._resolve(a, plain_literal=True) for a in s.inputs]
            if any(a is None for a in args):
                raise _Skip()
            self.env[s.out] = TRANSFORMS[s.fn](*args)
        elif s.kind == "declass":
            args = [self._resolve(a) for a in s.inputs]
            if any(a is None for a in args):
                raise _Skip()
            if not self.enforce and s.naive is not None:
                self.env[s.out] = self._resolve(s.naive)  # undefended agent trusts the text it read
                return
            try:
                self.env[s.out] = VALIDATORS[s.fn](*args, self.world)
            except DeclassifyError:
                fallback = self._resolve(s.naive) if s.naive is not None else args[0]
                self.env[s.out] = fallback  # stays untrusted; the gate will deny it at the sink
        elif s.kind == "call":
            args = {k: self._resolve(v) for k, v in s.args.items()}
            if any(v is None for v in args.values()):
                raise _Skip()
            res = self.invoke(s.tool, args, s.call_id, planned=True)
            if res is not None and s.out:
                self.env[s.out] = res
            elif s.out:
                raise _Skip()

    # ---- the gate -----------------------------------------------------------------
    def _alert(self, call_id: str, tool: str, chain: str, reason: str) -> None:
        self.alerts += 1
        self.emit("alert", call_id=call_id, tool=tool, chain=chain, reason=reason)

    def _plain(self, args: dict[str, Any]) -> dict[str, str]:
        return {k: str(raw(v))[:120] for k, v in args.items()}

    def invoke(self, tool: str, args: dict[str, LabeledObject], call_id: str, planned: bool) -> Optional[LabeledObject]:
        sensitive = tool in {"send_email", "reply_email", "transfer_money", "read_file", "write_file",
                             "web_fetch", "calendar_add"}
        if planned and sensitive:
            self.legit_sensitive += 1
        t0 = time.perf_counter()
        denied_reason = None
        checks = []
        if self.enforce:
            if not planned and self.plan_guard:
                denied_reason = "call is not in the plan fixed from the user's request"
                checks = [(k, v, Decision(False, denied_reason)) for k, v in args.items()]
            else:
                for k, v in args.items():
                    d = self.policy.check(tool, k, v)
                    checks.append((k, v, d))
                    if not d.allow and denied_reason is None:
                        denied_reason = d.reason
        self.gate_ms.append((time.perf_counter() - t0) * 1000)

        first_bad = None
        for item in checks:
            if item is None:
                continue
            k, v, d = item
            self.emit("call_check", call_id=call_id, tool=tool, argument=k, value_id=v.vid,
                      decision="allow" if d.allow else "deny", reason=d.reason,
                      sources=v.label.source_names(), trust=v.label.trust.name)
            if not d.allow and first_bad is None:
                first_bad = (k, v)
        if not self.enforce:
            for k, v in args.items():
                self.emit("call_check", call_id=call_id, tool=tool, argument=k, value_id=v.vid, decision="allow",
                          reason="undefended: no policy gate", sources=v.label.source_names(),
                          trust=v.label.trust.name)

        # advisory sentinel (D3) or deciding sentinel (D4)
        warn = None
        if self.defence in ("D3", "D4"):
            r = self.sentinel.score(self.request, tool, self._plain(args))
            self.laya_ms.append(r.ms)
            self.emit("laya_score", call_id=call_id, score=r.score, ms=round(r.ms, 2), warn=r.warn)
            warn = r.warn
            if r.warn:
                self.laya_warns.append({"call_id": call_id, "tool": tool, "planned": planned})
            if self.defence == "D4" and r.warn:
                denied_reason = "sentinel says the call does not fit the task"

        if denied_reason is not None:
            if first_bad is not None:
                k, v = first_bad
                chain = f"{k} <- {self.audit.chain(v.vid)} <- {', '.join(v.label.source_names())}, {v.label.trust.name}"
            elif args:
                k, v = next(iter(args.items()))
                chain = f"{k} <- {self.audit.chain(v.vid)} <- {', '.join(v.label.source_names())}, {v.label.trust.name}"
                if not planned:
                    chain = f"{tool}({chain})"
            else:
                chain = tool
            self._alert(call_id, tool, chain, denied_reason)
            self.denied.append({"call_id": call_id, "tool": tool, "planned": planned, "reason": denied_reason})
            if planned and sensitive:
                self.legit_denied += 1
            return None

        return self._execute(tool, args, call_id)

    def _execute(self, tool: str, args: dict[str, LabeledObject], call_id: str) -> LabeledObject:
        n_before = len(self.world.effects)
        plain = {k: raw(v) for k, v in args.items()}
        for k, v in args.items():
            v.reveal(f"sink {tool}.{k}")
        out = self.world.call(tool, **self._maybe_filter(tool, plain))
        # label store: remember what was written
        if tool == "write_file" and self.use_labelstore:
            content = args["content"]
            self.world.labelstore[plain["path"]] = content.label
        for e in self.world.effects[n_before:]:
            e["call_id"] = call_id
            self.emit("effect", call_id=call_id, kind=e["kind"], description=e["description"],
                      leak=self.world.is_leak(e))
        res = self._wrap(tool, plain, out)
        self.emit("tool_result", call_id=call_id, tool=tool, value_id=res.vid, sources=res.label.source_names(),
                  trust=res.label.trust.name, preview=str(raw(res))[:80])
        if self.follow and tool in TEXT_TOOLS:
            self._follow_injections(tool, res, call_id)
        return res

    def _maybe_filter(self, tool, plain):
        return plain

    # ---- wrapping tool outputs ----------------------------------------------------
    def _wrap(self, tool: str, plain: dict[str, Any], out: Any) -> LabeledObject:
        if self.defence == "D1" and tool in TEXT_TOOLS:
            out = filter_value(out)
        if tool == "read_inbox":
            items = []
            for m in out:
                nm = f"email#{m['id']}"
                items.append(lodict({k: source_obj(v, Source.EMAIL, nm) for k, v in m.items() if k != "unread"},
                                    name=nm))
            return lolist(items, name="inbox")
        if tool == "read_file":
            lb = Label(Source.FILE, Trust.UNTRUSTED)
            stored = self.world.labelstore.get(plain["path"]) if self.use_labelstore else None
            if stored is not None:
                lb = join(lb, stored)
            return LabeledObject(out, lb, name=f"file:{plain['path']}")
        if tool == "web_fetch":
            return source_obj(out, Source.WEB, "web:" + plain["url"].split("/")[2] if "//" in plain["url"] else "web")
        if tool == "search_docs":
            return lolist([lodict({k: source_obj(v, Source.TOOL_OTHER, "search_docs") for k, v in h.items()},
                                  name="search_docs") for h in out], name="search_docs")
        return source_obj(out, Source.TOOL_OTHER, tool + "_result")

    # ---- the simulated compliant agent --------------------------------------------
    def _texts(self, res: LabeledObject) -> list[LabeledObject]:
        v = res.value
        if isinstance(v, str):
            return [res]
        texts: list[LabeledObject] = []
        for item in res:
            if isinstance(item.value, dict):
                for key in ("subject", "body", "snippet"):
                    if key in item.value:
                        texts.append(item[key])
            elif isinstance(item.value, str):
                texts.append(item)
        return texts

    def _follow_injections(self, tool: str, res: LabeledObject, parent_call: str) -> None:
        for d in parse_directives(self._texts(res)):
            prev: Optional[LabeledObject] = None
            for tool2, a in d.steps:
                self._xn += 1
                cid = f"x{self._xn}"
                args = {}
                for k, v in a.items():
                    if v == "$prev":
                        v = prev
                    elif isinstance(v, tuple) and v[0] == "concat":
                        v = v[1] + (v[2] if v[2] != "$prev" else prev)
                    args[k] = v
                if any(v is None for v in args.values()):
                    break
                prev = self.invoke(tool2, args, cid, planned=False)
                if prev is None:
                    break


class _Skip(Exception):
    pass
