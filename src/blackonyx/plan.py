"""Plan format: a fixed, linear list of steps fixed from the user's request alone."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class Ref:
    name: str


@dataclass
class Step:
    kind: str                       # "call" | "xform" | "declass"
    out: Optional[str] = None
    tool: str = ""                  # call: tool name
    fn: str = ""                    # xform: function / declass: validator name
    args: dict[str, Any] = field(default_factory=dict)   # call: named args (Ref or literal)
    inputs: list[Any] = field(default_factory=list)       # xform/declass positional inputs
    naive: Optional[Any] = None     # declass: what an undefended agent uses instead (Ref)
    call_id: Optional[str] = None
    desc: str = ""


@dataclass
class Plan:
    task_id: str
    request: str
    steps: list[Step]

    def calls(self) -> list[Step]:
        return [s for s in self.steps if s.kind == "call"]

    def planned_tools(self) -> list[str]:
        return [s.tool for s in self.calls()]

    def validate(self) -> None:
        defined: set[str] = set()
        for s in self.steps:
            refs = [v for v in list(s.args.values()) + list(s.inputs) + [s.naive] if isinstance(v, Ref)]
            for v in list(s.args.values()) + list(s.inputs):
                if isinstance(v, list):
                    refs += [x for x in v if isinstance(x, Ref)]
            for r in refs:
                if r.name not in defined:
                    raise ValueError(f"step {s.out or s.tool} uses undefined {r.name}")
            if s.out:
                defined.add(s.out)


def call(tool: str, out: Optional[str] = None, desc: str = "", **args: Any) -> Step:
    return Step("call", out=out, tool=tool, args=args, desc=desc or tool)


def xform(fn: str, out: str, *inputs: Any) -> Step:
    return Step("xform", out=out, fn=fn, inputs=list(inputs), desc=fn)


def declass(validator: str, out: str, *inputs: Any, naive: Any = None) -> Step:
    return Step("declass", out=out, fn=validator, inputs=list(inputs), naive=naive, desc=validator)
