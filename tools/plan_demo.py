"""Real parcel (TKGM + neighbour evidence) -> plan -> validate -> compile -> out/.

usage: uv run python tools/plan_demo.py
writes out/{spec,ops}.json, model.ifc, report.html
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from brain.backends import IfcBackend
from brain.compiler import compile_spec
from brain.planner import plan_building
from brain.report import render_report
from brain.validate import validate_spec
from tests.helpers import RULES, load_demo_zoning, load_real_parcel


def run(out: Path | None = None, ends: list[str] | None = None) -> dict:
    out = out or ROOT / "out"
    out.mkdir(exist_ok=True)
    parcel, params = load_real_parcel(), load_demo_zoning()
    spec = plan_building(parcel, params, ends=ends)
    res = validate_spec(spec, parcel=parcel, params=params, rules=RULES)
    ops = compile_spec(spec)
    (out / "spec.json").write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    (out / "ops.json").write_text(json.dumps([o.model_dump() for o in ops], indent=1,
                                             ensure_ascii=False), encoding="utf-8")
    IfcBackend().write(spec, out / "model.ifc")
    (out / "report.html").write_text(render_report(parcel, res.zoning, params, spec.footprints), encoding="utf-8")
    summary = {"spec_id": spec.spec_id, "ops": len(ops), "walls": len(spec.walls),
               "rooms": len(spec.rooms), "ok": res.ok,
               "errors": [i.model_dump() for i in res.errors()],
               "warnings": [i.model_dump() for i in res.issues if i.level == "warn"],
               "zoning": res.zoning.verdict, "derived": spec.derived.model_dump()}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    run()
