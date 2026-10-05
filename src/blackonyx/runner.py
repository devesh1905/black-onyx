"""run_scenario: run a task (optionally under attack) under a defence and return the events."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .audit import Audit
from .interpreter import Interpreter
from .planner import plan_for
from .policy import Policy
from .scenarios.attacks import ATTACKS
from .scenarios.tasks import CHECKS
from .sentinel import Sentinel
from .world import World, build_world


@dataclass
class RunResult:
    events: list[dict[str, Any]]
    world: World
    task_id: str
    attack_id: Optional[str]
    defence: str
    task_ok: bool
    leaked: bool
    alerts: int
    gate_ms: list[float] = field(default_factory=list)
    laya_ms: list[float] = field(default_factory=list)
    legit_sensitive: int = 0
    legit_denied: int = 0
    laya_warns: list[dict] = field(default_factory=list)
    denied: list[dict] = field(default_factory=list)


def run(task_id: str, attack_id: Optional[str] = None, defence: str = "D2", injected_text: Optional[str] = None,
        sentinel: Optional[Sentinel] = None, policy: Optional[Policy] = None, log_path=None,
        variant_text: Optional[str] = None, **interp_kw: Any) -> RunResult:
    """task_id is the user's task. With attack_id, the attack's own host tasks are run first
    (A6 runs L5 then L9); pass task_id=None-like behaviour by using the attack's host task."""
    world = build_world()
    attack = ATTACKS.get(attack_id) if attack_id else None
    tasks = [task_id]
    if attack:
        tasks = list(attack.host_tasks)
        attack.apply(world, variant_text)
    if injected_text:  # live injection from the UI: a new unread email from an outside sender
        world.inbox.append({"id": max(m["id"] for m in world.inbox) + 1,
                            "from": "Unknown <unknown@outside.example>", "subject": "Hello",
                            "body": injected_text, "unread": True})
    with Audit(log_path) as audit:
        ip = None
        for t in tasks:
            ip = Interpreter(world, defence, policy=policy, sentinel=sentinel, audit=audit, **interp_kw)
            ip.run(plan_for(t))
            ip_last = ip
    final = tasks[-1]
    res = RunResult(events=audit.events, world=world, task_id=final, attack_id=attack_id, defence=defence,
                    task_ok=CHECKS[final](world), leaked=bool(world.leaks()), alerts=ip_last.alerts,
                    gate_ms=ip_last.gate_ms, laya_ms=ip_last.laya_ms, legit_sensitive=ip_last.legit_sensitive,
                    legit_denied=ip_last.legit_denied, laya_warns=ip_last.laya_warns, denied=ip_last.denied)
    return res


def run_scenario(task_id: str, attack_id: Optional[str], defence: str, injected_text: Optional[str] = None,
                 sentinel: Optional[Sentinel] = None) -> list[dict[str, Any]]:
    """Entry point for the UI: returns the list of event dicts."""
    return run(task_id, attack_id or None, defence, injected_text, sentinel).events
