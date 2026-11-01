"""Build out/report.html from a parcel fixture + zoning yaml.

usage: uv run python tools/make_report.py data/parcels/synthetic_12x25.manual.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from brain.parcel import assign_roles, parcel_from_local_ring, validate_parcel
from brain.report import render_report
from brain.rules import load_rules
from brain.schemas import ParcelSource
from brain.zoning import check_zoning, load_zoning


def main(fixture: str, zoning: str = "data/imar-durumu/demo.yaml") -> None:
    data = json.loads((ROOT / fixture).read_text(encoding="utf-8"))
    parcel = parcel_from_local_ring(
        data["parcel_id"], [tuple(p) for p in data["ring_local"]],
        source=ParcelSource(**data["source"]), area_tapu_m2=data.get("area_tapu_m2"))
    parcel = assign_roles(parcel, {int(k): v for k, v in data["roles"].items()})
    errors = [i for i in validate_parcel(parcel) if i.level == "error"]
    if errors:
        raise SystemExit(f"parcel invalid: {errors}")
    params = load_zoning(ROOT / zoning)
    rules = load_rules(ROOT / "data/rules/paiy-2017.yaml")
    footprint = data.get("demo_footprint")
    report = check_zoning(
        parcel, params, footprint=footprint, floors=3 if footprint else None,
        floor_height_m=3.0 if footprint else None, rules=rules)
    out = ROOT / "out" / "report.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(render_report(parcel, report, params), encoding="utf-8")
    print(f"wrote {out} · verdict={report.verdict} · buildable={report.buildable_area_m2} m2")


if __name__ == "__main__":
    main(*sys.argv[1:])
