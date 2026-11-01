"""A Revit stand-in for tests: derives the read-back a perfect add-in would return from a spec."""

from __future__ import annotations

import math
from typing import Any

from shapely.geometry import Polygon

from brain.backends.revit import BridgeUnavailable, RevitBackend
from brain.brick import expected_pieces
from brain.compiler import compile_spec
from brain.schemas import BuildingSpec

SUPPORTED = ["create_level", "create_wall", "create_floor", "create_room", "create_stair", "create_roof",
             "place_door", "place_window", "create_brick_panel", "tag_room"]


def model_from_spec(spec: BuildingSpec, lod: str = "courses") -> dict[str, Any]:
    """What a faithful Revit model of `spec` reads back as (walls a little longer where they butt)."""
    return {
        "title": "fake",
        "counts": {"levels": len(spec.levels), "walls": len(spec.walls), "floors": len(spec.slabs),
                   "rooms": len(spec.rooms), "doors": sum(o.kind == "door" for o in spec.openings),
                   "windows": sum(o.kind == "window" for o in spec.openings), "stairs": len(spec.stairs),
                   "roofs": len(spec.roofs), "room_tags": len(spec.rooms)},
        "tagged": 0, "warnings": 3, "warning_kinds": [{"text": "Highlighted walls overlap.", "count": 3}],
        "walls": [{"spec_ref": w.id, "length_m": round(math.dist(w.a, w.b) + 0.1, 4),
                   "thickness_m": w.thickness, "height_m": w.height} for w in spec.walls],
        "floors": [{"spec_ref": s.id, "area_m2": round(
            Polygon(s.outline).area - sum(Polygon(o).area for o in s.openings), 4)} for s in spec.slabs],
        "rooms": [{"spec_ref": r.id, "name": r.name, "area_m2": round(Polygon(r.outline).area, 4),
                   "placed": True} for r in spec.rooms],
        "stairs": [{"spec_ref": s.id, "risers": sum(s.risers), "riser_h_m": s.riser_h, "tread_d_m": s.tread_d,
                    "z_min_m": next(l.elevation for l in spec.levels if l.id == s.from_level),
                    "z_max_m": next(l.elevation for l in spec.levels if l.id == s.to_level)}
                   for s in spec.stairs],
        "brick_panels": [{"spec_ref": ref, "comments": f"klinker pieces={n}; faces=0; lod={lod}"}
                         for ref, n in expected_pieces(compile_spec(spec), lod).items()],
        "openings": [{"spec_ref": o.id, "category": "Doors" if o.kind == "door" else "Windows"}
                     for o in spec.openings],
    }


class FakeRevit(RevitBackend):
    """Overrides the transport; `spec` is what the "model" will contain after apply."""

    def __init__(self, online: bool = True):
        super().__init__(endpoint_file="unused")
        self.online = online
        self.spec: BuildingSpec | None = None
        self.applied: list[dict[str, Any]] = []
        self.project: str | None = None
        self.lod = "full"

    def call(self, method: str, **params: Any) -> Any:
        if not self.online:
            raise BridgeUnavailable("fake bridge offline")
        if method == "ping":
            return {"pong": True, "ops": SUPPORTED, "ops_version": "fake"}
        if method == "status":
            return {"revit": {"name": "Fake Revit"}, "documents": 1}
        if method == "new_project":
            self.project = params["path"]
            return {"path": params["path"], "title": "fake"}
        if method == "apply_ops":
            self.applied.append(params)
            lods = {o["args"]["lod"] for o in params["ops"] if o["op"] == "create_brick_panel"}
            self.lod = lods.pop() if lods else self.lod
            n = len(params["ops"])
            return {"created": 0 if params["dry_run"] else n, "updated": 0, "unchanged": 0, "deleted": 0,
                    "dry_run": params["dry_run"], "warnings": []}
        if method == "read_back":
            assert self.spec is not None, "set FakeRevit.spec first"
            return model_from_spec(self.spec, self.lod)
        if method == "export_ifc":
            from pathlib import Path
            from brain.backends.ifc import IfcBackend
            assert self.spec is not None
            out = Path(params["dir"]) / params["name"]
            IfcBackend().write(self.spec, out)
            return {"ok": True, "path": str(out), "bytes": out.stat().st_size}
        if method == "show_3d":
            return {"view": "RB 3D"}
        if method == "export_views":
            return {"dir": params["dir"], "files": []}
        raise AssertionError(f"unexpected method {method}")
