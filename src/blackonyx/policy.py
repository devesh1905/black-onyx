"""YAML policy gate: per tool, per argument, which origins and trust are acceptable."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from .labeled import LabeledObject, raw
from .labels import Source, Trust

DEFAULT_POLICY = Path(__file__).resolve().parents[2] / "policy" / "policy.yaml"


@dataclass
class Decision:
    allow: bool
    reason: str
    kind: str = "data"


class Policy:
    def __init__(self, spec: dict[str, Any]):
        self.tools: dict[str, dict[str, Any]] = spec.get("tools", {})

    @classmethod
    def load(cls, path: str | Path = DEFAULT_POLICY) -> "Policy":
        return cls(yaml.safe_load(Path(path).read_text(encoding="utf-8")))

    def known_tool(self, tool: str) -> bool:
        return tool in self.tools

    def check(self, tool: str, arg: str, value: LabeledObject) -> Decision:
        if tool not in self.tools:
            return Decision(False, f"tool '{tool}' is not in the policy")
        rule = self.tools[tool].get(arg)
        if rule is None:
            return Decision(False, f"argument '{arg}' of '{tool}' has no policy rule")
        kind = rule.get("kind", "data")
        if kind == "data":
            return Decision(True, "data argument: any trust", kind)
        lb = value.label
        allowed = Source.NONE
        for s in rule.get("sources", []):
            allowed |= Source[s]
        min_trust = Trust[rule.get("min_trust", "VERIFIED")]
        extra = lb.sources & ~allowed
        if not extra and lb.trust >= min_trust:
            return Decision(True, f"origin {lb} is allowed for {tool}.{arg}", kind)
        if "allow_hosts" in rule:
            u = urlparse(str(raw(value)))
            if u.hostname in rule["allow_hosts"] and not ((u.query or u.fragment or u.params) and not rule.get("untrusted_query", False)):
                return Decision(True, f"allowlisted host {u.hostname}, no untrusted query/fragment data", kind)
        if extra:
            names = "|".join(s.name for s in Source if s != Source.NONE and s in extra)
            why = f"{tool}.{arg} may not come from {names} (allowed: {', '.join(rule.get('sources', []))})"
        else:
            why = f"{tool}.{arg} needs trust >= {min_trust.name}, got {lb.trust.name}"
        return Decision(False, why, kind)
