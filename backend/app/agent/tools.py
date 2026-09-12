"""Typed tool registry with RBAC + approval policy.

Every agent capability is a registered function with:
  - name / description (stable contract for plans)
  - risk tier: read | write_internal | needs_approval
  - allowed roles (viewer may read, analyst+ may write, admin for destructive)
  - timeout + cost budget (runaway protection, per-step caps)

The runner enforces these before execution and writes an AuditEvent per call.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable


READ = "read"
WRITE_INTERNAL = "write_internal"
NEEDS_APPROVAL = "needs_approval"

RISKS = (READ, WRITE_INTERNAL, NEEDS_APPROVAL)

# Role hierarchy: viewer < analyst < admin
_ROLE_RANK = {"viewer": 0, "analyst": 1, "admin": 2}


@dataclass
class ToolContext:
    """What a tool may act with. No raw infra access."""

    db: Any
    user: Any
    org_id: str
    run_id: str
    step_seq: int


@dataclass
class ToolSpec:
    name: str
    description: str
    risk: str = READ
    min_role: str = "viewer"
    timeout_seconds: int = 60
    cost: int = 1
    func: Callable[..., dict] = field(default=lambda ctx, **kw: {"ok": True})

    def allows(self, role: str) -> bool:
        return _ROLE_RANK.get(str(role), -1) >= _ROLE_RANK.get(self.min_role, 99)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> ToolSpec:
        if spec.risk not in RISKS:
            raise ValueError(f"unknown risk tier: {spec.risk}")
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = spec
        return spec

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError:
            raise KeyError(f"Unknown tool: {name}")

    def list(self) -> list[ToolSpec]:
        return [self._tools[k] for k in sorted(self._tools)]

    def describe(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "risk": t.risk,
                "min_role": t.min_role,
                "timeout_seconds": t.timeout_seconds,
                "cost": t.cost,
            }
            for t in self.list()
        ]


registry = ToolRegistry()


def quantive_tool(
    name: str,
    description: str,
    risk: str = READ,
    min_role: str = "viewer",
    timeout_seconds: int = 60,
    cost: int = 1,
):
    """Decorator to register an agent tool.

    Example:
        @quantive_tool("portfolio_summary", "Summarize a portfolio", risk="read")
        def portfolio_summary(ctx: ToolContext, portfolio_id: str) -> dict: ...
    """

    def deco(fn: Callable[..., dict]) -> Callable[..., dict]:
        # Validate signature: first param must accept ctx
        sig = inspect.signature(fn)
        params = list(sig.parameters)
        if not params:
            raise TypeError(f"tool {name} must accept ctx as first arg")
        spec = ToolSpec(
            name=name,
            description=description,
            risk=risk,
            min_role=min_role,
            timeout_seconds=timeout_seconds,
            cost=cost,
            func=fn,
        )
        registry.register(spec)
        return fn

    return deco
