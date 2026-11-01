"""Scenario S-B: change the storey height and let the diff update the model.

usage: uv run python tools/scenario_b.py [--height 2.9]
Needs Revit with the project from tools/build_in_revit.py --new-project already built at 3.00 m.
Steps: plan at 3.00 -> apply (expect 0 changes) -> plan at the new height -> apply (only affected elements
change) -> verify_model -> apply the same plan again (0 changes) -> restore 3.00 -> verify.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from brain.service import Session

PARCEL = "karatay-buyuksinan-1495-26"


def counts(r: dict) -> str:
    return f"created {r['created']}, updated {r['updated']}, unchanged {r['unchanged']}"


def run(height: float = 2.9, verbose: bool = False) -> list[tuple[str, bool, str]]:
    s = Session()
    s.load_parcel(PARCEL)
    s.check_zoning()
    results: list[tuple[str, bool, str]] = []

    def step(name: str, ok: bool, detail: str) -> None:
        results.append((name, ok, detail))
        if verbose:
            print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")

    s.plan_building(floor_height_m=3.0)
    r = s.build_in_revit(dry_run=False)
    step("baseline 3.00 m applies as 0 changes", r["ok"] and r["created"] == r["updated"] == 0, counts(r) if r["ok"] else r["error"])

    p = s.plan_building(floor_height_m=height)
    step(f"plan at {height:.2f} m is valid", p["ok"] and p["validation"]["ok"],
         f"spec {p['spec_id']}, errors {len(p['validation']['errors'])}" if p["ok"] else p["error"])
    if not p["ok"]:
        return results
    r = s.build_in_revit(dry_run=False)
    changed = r["created"] + r["updated"]
    step(f"apply {height:.2f} m", r["ok"] and changed > 0, counts(r) if r["ok"] else r["error"])
    v = s.verify_model()
    step(f"model matches the {height:.2f} m spec", v["ok"], f"{len(v['differences'])} difference(s)")
    for d in v["differences"][:10]:
        print("      -", d)

    r2 = s.build_in_revit(dry_run=False)
    step("second apply is a no-op", r2["ok"] and r2["created"] == r2["updated"] == 0, counts(r2) if r2["ok"] else r2["error"])

    s.plan_building(floor_height_m=3.0)
    r3 = s.build_in_revit(dry_run=False)
    v3 = s.verify_model()
    step("restore 3.00 m", r3["ok"] and v3["ok"], f"{counts(r3)}; {len(v3['differences'])} difference(s)")
    return results


def main() -> int:
    height = float(sys.argv[sys.argv.index("--height") + 1]) if "--height" in sys.argv else 2.9
    results = run(height, verbose=True)
    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
