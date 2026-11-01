"""PAİY rule catalogue (data/rules/paiy-2017.yaml): loading and default-setback checks."""

from __future__ import annotations

import operator
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict

from .schemas import Check, Citation, ZoningParams

_OPS = {">=": operator.ge, "<=": operator.le, "==": operator.eq}


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    article: str
    summary: str
    param: str | None = None
    op: Literal[">=", "<=", "==", "between"] | None = None
    value: float | list[float] | None = None
    unit: str | None = None
    overridable_by_plan: bool = False
    verified: bool = False

    def citation(self) -> Citation:
        return Citation(ref=f"PAİY {self.article}", verified=self.verified)

    def holds(self, actual: float) -> bool:
        if self.op is None or self.value is None:
            raise ValueError(f"rule {self.id} has no numeric condition")
        if self.op == "between":
            lo, hi = self.value  # type: ignore[misc]
            return lo <= actual <= hi
        return _OPS[self.op](actual, self.value)


def load_rules(path: str | Path) -> dict[str, Rule]:
    data: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    rules = [Rule.model_validate(r) for r in data["rules"]]
    ids = [r.id for r in rules]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate rule ids in rule file")
    return {r.id: r for r in rules}


def check_setback_defaults(params: ZoningParams, rules: dict[str, Rule]) -> list[Check]:
    """Compare the plan's setbacks with PAİY Madde 23 defaults.

    The defaults only apply where the plan is silent, so a lower value is a warning
    ("valid only if the plan overrides"), never a failure.
    """
    out: list[Check] = []
    for rule in rules.values():
        if not rule.param or not rule.param.startswith("setbacks."):
            continue
        actual = getattr(params.setbacks, rule.param.split(".", 1)[1])
        ok = rule.holds(actual)
        out.append(Check(
            id=f"Z-{rule.id}",
            status="pass" if ok else "warn",
            actual=actual,
            limit=float(rule.value),  # type: ignore[arg-type]
            message=(f"{rule.summary}; plan value {actual} m" if ok else
                     f"{rule.summary}; plan value {actual} m is below the PAİY default and is "
                     f"valid only if the plan notes override it (Madde 23(1) 'aksine hüküm')"),
            citation=rule.citation(),
        ))
    return out
