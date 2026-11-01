"""IFC side of the three-way consistency check (spec <-> Revit <-> IFC): counts per class and room area."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.util.element as element
from shapely.geometry import Polygon

from .schemas import BuildingSpec

AREA_REL_TOL = 0.02


def ifc_summary(path: str | Path) -> dict[str, Any]:
    f = ifcopenshell.open(str(path))

    def count(cls: str) -> int:
        return len(f.by_type(cls))

    net = 0.0
    with_qto = 0
    for sp in f.by_type("IfcSpace"):
        for _, props in element.get_psets(sp, qtos_only=True).items():
            if "NetFloorArea" in props:
                net += float(props["NetFloorArea"])
                with_qto += 1
    return {
        "schema": f.schema,
        "walls": count("IfcWall"), "slabs": count("IfcSlab"), "roofs": count("IfcRoof"),
        "spaces": count("IfcSpace"), "doors": count("IfcDoor"), "windows": count("IfcWindow"),
        "stairs": count("IfcStair"), "storeys": count("IfcBuildingStorey"),
        "brick_panels": sum(1 for p in f.by_type("IfcBuildingElementProxy") if (p.Name or "").startswith("BP-")),
        "space_net_area_m2": round(net, 3) if with_qto else None, "spaces_with_area": with_qto,
        "buildings": [b.Name for b in f.by_type("IfcBuilding")],
    }


def compare_ifc(spec: BuildingSpec, path: str | Path) -> dict[str, Any]:
    """Rows of (what, spec, ifc, ok) plus a list of differences."""
    s = ifc_summary(path)
    want_doors = sum(o.kind == "door" for o in spec.openings)
    rows = [
        ("IfcWall", len(spec.walls), s["walls"], s["walls"] == len(spec.walls)),
        ("IfcSpace", len(spec.rooms), s["spaces"], s["spaces"] == len(spec.rooms)),
        ("IfcDoor", want_doors, s["doors"], s["doors"] == want_doors),
        ("IfcWindow", len(spec.openings) - want_doors, s["windows"], s["windows"] == len(spec.openings) - want_doors),
        ("IfcStair", len(spec.stairs), s["stairs"], s["stairs"] == len(spec.stairs)),
        ("IfcBuildingStorey", len(spec.levels), s["storeys"], s["storeys"] == len(spec.levels)),
        ("IfcSlab (>= floor slabs)", len(spec.slabs), s["slabs"], s["slabs"] >= len(spec.slabs)),
    ]
    want_area = sum(Polygon(r.outline).area for r in spec.rooms)
    if s["space_net_area_m2"] is not None:
        ok = abs(s["space_net_area_m2"] - want_area) <= AREA_REL_TOL * want_area
        rows.append(("space net area m2", round(want_area, 2), s["space_net_area_m2"], ok))
    diffs = [f"{what}: spec {a} vs IFC {b}" for what, a, b, ok in rows if not ok]
    return {"ok": not diffs, "summary": s, "rows": [dict(what=w, spec=a, ifc=b, ok=ok) for w, a, b, ok in rows],
            "differences": diffs}
