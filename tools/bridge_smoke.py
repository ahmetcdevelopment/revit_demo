"""P3 smoke test against a running Revit with the add-in loaded.

usage: uv run python tools/bridge_smoke.py [--new-project]
Checks: ping, status, (new project), apply create_level twice (idempotency), rollback on a bad op,
dry-run leaves the model untouched, read_back counts.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from brain.backends.revit import BridgeUnavailable, RevitBackend, RevitBridgeError
from brain.compiler import compile_spec
from brain.planner import plan_building
from brain.schemas import Op
from tests.helpers import load_demo_zoning, load_real_parcel


def step(name: str, value) -> None:
    print(f"[{name}] {value}")


def main() -> int:
    rb = RevitBackend()
    try:
        step("ping", rb.ping())
    except BridgeUnavailable as e:
        print("Revit bridge not reachable:", e)
        return 2
    step("status", rb.status())
    if "--new-project" in sys.argv:
        step("new_project", rb.new_project(ROOT / "out" / "karatay_1495_26.rvt"))

    spec = plan_building(load_real_parcel(), load_demo_zoning())
    levels = [o for o in compile_spec(spec) if o.op == "create_level"]

    before = rb.read_back()
    step("dry_run", rb.apply_ops(levels, spec.spec_id, dry_run=True)["created"])
    assert rb.read_back()["counts"]["levels"] == before["counts"]["levels"], "dry run changed the model"

    first = rb.apply_ops(levels, spec.spec_id)
    step("apply #1", {k: first[k] for k in ("created", "updated", "unchanged")})
    second = rb.apply_ops(levels, spec.spec_id)
    step("apply #2 (idempotent)", {k: second[k] for k in ("created", "updated", "unchanged")})
    assert second["created"] == 0 and second["updated"] == 0 and second["unchanged"] == len(levels)

    moved = [Op(op_id=o.op_id, op=o.op, spec_ref=o.spec_ref, depends_on=o.depends_on,
                args={**o.args, "elevation": o.args["elevation"] + 0.1}) for o in levels[:1]]
    step("apply #3 (changed elevation)", rb.apply_ops(moved, spec.spec_id)["updated"])
    rb.apply_ops(levels[:1], spec.spec_id)   # put it back

    try:
        bad = levels[:1] + [Op(op_id="9999", op="create_wall", spec_ref="W-X", depends_on=[], args={})]
        rb.apply_ops(bad, spec.spec_id)
    except RevitBridgeError as e:
        step("bad op rejected", e)
    step("read_back", rb.read_back())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
