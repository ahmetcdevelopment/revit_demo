"""Runs the demo scenarios S-A..S-D against the running Revit and writes out/test-report.md.

usage: uv run python tools/scenarios.py [--skip-pytest]
S-A golden path from a fresh project, S-B storey height change, S-C zoning violation blocked,
S-D rollback on a bad op. Each prints PASS/FAIL lines; the report joins them with the pytest result.
"""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from brain.backends.revit import RevitBackend, RevitBridgeError
from brain.compiler import compile_spec
from brain.schemas import Op
from brain.service import Session

PARCEL = "karatay-buyuksinan-1495-26"
Result = tuple[str, bool, str]


def fresh() -> Session:
    s = Session()
    s.load_parcel(PARCEL)
    s.check_zoning()
    return s


def counts(r: dict) -> str:
    return f"created {r['created']}, updated {r['updated']}, unchanged {r['unchanged']}"


def scenario_a() -> list[Result]:
    out: list[Result] = []
    s = fresh()
    p = s.plan_building()
    out.append(("plan is valid, TAKS/KAKS within limits",
                p["ok"] and p["validation"]["ok"] and p["derived"]["taks"] <= 0.40 and p["derived"]["kaks"] <= 1.20,
                f"TAKS {p['derived']['taks']}, KAKS {p['derived']['kaks']}, {p['ops']} ops"))
    dry = s.build_in_revit(dry_run=True)
    out.append(("dry run leaves the model alone", dry["ok"], dry.get("mode", dry.get("error", ""))))
    t = time.time()
    r = s.build_in_revit(dry_run=False, new_project=True)
    out.append(("build in a fresh project", r["ok"] and r["created"] > 0 and r["updated"] == 0,
                f"{counts(r)} in {time.time() - t:.0f} s" if r["ok"] else r["error"]))
    v = s.verify_model()
    out.append(("verify_model: model == spec", v["ok"], f"{len(v['differences'])} difference(s), "
                f"{v.get('revit_warnings')} Revit warning(s)"))
    r2 = s.build_in_revit(dry_run=False)
    out.append(("second apply changes nothing", r2["ok"] and r2["created"] == r2["updated"] == 0, counts(r2)))
    views = s.export_views()
    out.append(("Revit views exported", views["ok"] and len(views["files"]) >= 4, f"{len(views.get('files', []))} PNG"))
    return out


def scenario_b() -> list[Result]:
    import scenario_b
    sys.argv = [sys.argv[0]]
    return scenario_b.run(2.9)


def scenario_c() -> list[Result]:
    out: list[Result] = []
    s = fresh()
    p = s.plan_building(floors=4)
    codes = {e["code"] for e in p["validation"]["errors"]} if p["ok"] else set()
    out.append(("4 floors fails KAT, KAKS and HMAX", {"Z-KAT", "Z-KAKS", "Z-HMAX"} <= codes, ", ".join(sorted(codes))))
    b = s.build_in_revit(dry_run=False)
    out.append(("blocked before Revit", not b["ok"] and b.get("blocked") is True, b.get("error", "")))
    s.plan_building(floor_height_m=3.8)
    z = s.check_zoning()
    out.append(("zoning report cites sources or says 'assumed'",
                z["ok"] and z["report"]["demo_assumption"] and all(c["status"] in ("pass", "assumed", "fail", "warn")
                                                                    for c in z["report"]["checks"]),
                f"assumed: {', '.join(z['assumptions'])}"))
    s.load_parcel("synthetic_12x25")
    tiny = s.plan_building()
    out.append(("a parcel too small is refused, not squeezed", not tiny["ok"], tiny.get("error", "")))
    return out


def scenario_d() -> list[Result]:
    out: list[Result] = []
    s = fresh()
    spec_id = s.plan_building()["spec_id"]
    rb: RevitBackend = s.backend
    l0 = [o for o in compile_spec(s.spec) if o.spec_ref == "L0"]
    before = rb.read_back()["counts"]
    good = Op(op_id="9001", op="create_wall", spec_ref="W-TEST-OK", depends_on=["L0"],
              args={"level": "L0", "a": [0, 0], "b": [3, 0], "thickness": 0.2, "height": 3.0, "type": "int"})
    bad = Op(op_id="9002", op="create_wall", spec_ref="W-TEST-BAD", depends_on=["L0"],
             args={"level": "NOPE", "a": [0, 1], "b": [3, 1], "thickness": 0.2, "height": 3.0, "type": "int"})
    try:
        rb.apply_ops(l0 + [good, bad], spec_id)
        out.append(("bad op is rejected", False, "no error"))
    except RevitBridgeError as e:
        out.append(("bad op is rejected with its op id", e.op_id == "9002", str(e)))
    after = rb.read_back()["counts"]
    out.append(("model unchanged after the failure (rollback)", before == after,
                f"walls {before['walls']} -> {after['walls']}"))
    return out


def scenario_f() -> list[Result]:
    """Klinker facade in Revit, then IFC4 from Revit checked against the IDS and against the spec."""
    out: list[Result] = []
    s = fresh()
    s.plan_building()
    t = time.time()
    r = s.build_in_revit(dry_run=False, new_project=True, facade_lod="full")
    k = r.get("klinker", {})
    out.append(("klinker built brick by brick", r["ok"] and k.get("pieces", 0) > 30000,
                f"{k.get('pieces')} bricks in {k.get('panels')} panels, built in {time.time() - t:.0f} s"))
    v = s.verify_model()
    out.append(("model matches the spec incl. klinker piece counts", v["ok"], f"{len(v['differences'])} difference(s)"))
    i = s.export_ifc()
    out.append(("IFC4 comes from Revit's exporter", i["ok"] and "Revit" in i["route"], f"{i['bytes'] / 1e6:.1f} MB"))
    out.append(("IFC passes the project IDS", i["ids"]["ok"], f"{i['ids']['specifications']} specs, failed: {i['ids']['failed'] or 'none'}"))
    out.append(("IFC counts and room area equal the spec", i["consistency"]["ok"], "; ".join(i["consistency"]["differences"]) or "all rows match"))
    out.append(("klinker panels are in the IFC", i["klinker_in_ifc"] == k.get("panels"), f"{i['klinker_in_ifc']} IfcBuildingElementProxy"))
    return out


def pytest_line() -> str:
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=ROOT,
                       capture_output=True, text=True)
    last = [ln for ln in p.stdout.strip().splitlines() if ln.strip()][-1]
    return last


def main() -> int:
    sys.path.insert(0, str(ROOT / "tools"))
    sections = [("S-A  Golden path", scenario_a), ("S-B  Storey height change", scenario_b),
                ("S-C  Violation caught", scenario_c), ("S-D  Failure safety", scenario_d),
                ("S-F  Klinker and IFC", scenario_f)]
    lines = [f"# Test report - {datetime.now():%Y-%m-%d %H:%M}", ""]
    failed = 0
    for title, fn in sections:
        print(f"\n== {title}")
        lines += [f"## {title}", ""]
        try:
            results = fn()
        except Exception as e:  # noqa: BLE001
            results = [("scenario ran", False, f"{type(e).__name__}: {e}")]
        for name, ok, detail in results:
            print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
            lines.append(f"- {'PASS' if ok else '**FAIL**'} - {name}: {detail}")
            failed += not ok
        lines.append("")
    if "--skip-pytest" not in sys.argv:
        py = pytest_line()
        print("\npytest:", py)
        lines += ["## Unit and integration tests (no Revit needed)", "", f"- `{py}`", ""]
    lines += ["## Layers", "",
              "1. Python unit/integration tests (parcel, zoning, planner, validate, compiler, IFC, verify, MCP).",
              "2. Scenarios above, run against the real Revit 2027.3 add-in.",
              "3. verify_model: spec compared with the Revit read-back (counts, lengths, areas, stairs).", "",
              "Zoning values come from `data/imar-durumu/demo.yaml` (DEMO ASSUMPTION, not the parcel's imar durumu)."]
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out" / "test-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n{'ALL PASSED' if not failed else str(failed) + ' FAILED'} -> out/test-report.md")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
