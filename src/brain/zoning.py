"""Zoning engine: edge-based setbacks, buildable area, TAKS/KAKS/height checks."""

from __future__ import annotations

from pathlib import Path

import yaml
from shapely.geometry import Polygon
from shapely.ops import unary_union

from .rules import Rule, check_setback_defaults
from .schemas import (
    Check,
    Citation,
    Edge,
    EdgeRole,
    ParcelSpec,
    Setbacks,
    ZoningParams,
    ZoningReport,
)

EPS = 1e-6
BIG = 1e4  # half-plane extent (m); parcels are far smaller


def load_zoning(path: str | Path) -> ZoningParams:
    return ZoningParams.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def setback_for(edge: Edge, sb: Setbacks) -> float:
    match edge.role:
        case EdgeRole.FRONT:
            return sb.front
        case EdgeRole.REAR:
            return sb.rear
        case EdgeRole.SIDE_FREE:
            return sb.side_free
        case EdgeRole.SIDE_PARTY:
            return sb.side_party
        case _:
            raise ValueError(f"edge {edge.i} has no role; assign edge roles first")


def _half_plane(edge: Edge, d: float) -> Polygon:
    """Region on the interior side of `edge` shifted inward by `d` (ring is CCW)."""
    (ax, ay), (bx, by) = edge.a, edge.b
    dx, dy = (bx - ax) / edge.length, (by - ay) / edge.length
    nx, ny = -dy, dx  # inward normal for CCW rings
    ax, ay, bx, by = ax + nx * d, ay + ny * d, bx + nx * d, by + ny * d
    return Polygon([
        (ax - dx * BIG, ay - dy * BIG),
        (bx + dx * BIG, by + dy * BIG),
        (bx + dx * BIG + nx * BIG, by + dy * BIG + ny * BIG),
        (ax - dx * BIG + nx * BIG, ay - dy * BIG + ny * BIG),
    ])


def buildable_polygon(parcel: ParcelSpec, sb: Setbacks) -> Polygon:
    """Parcel intersected with one inward-shifted half-plane per edge (edge-specific setbacks)."""
    area = Polygon(parcel.ring_local)
    for e in parcel.edges:
        d = setback_for(e, sb)
        if d > 0:
            area = area.intersection(_half_plane(e, d))
        if area.is_empty:
            return Polygon()
    if area.geom_type == "MultiPolygon":
        area = max(area.geoms, key=lambda g: g.area)
    return area.buffer(0) if not area.is_valid else area


def _citation(params: ZoningParams, field: str) -> Citation | None:
    return params.citations.get(field)


def _status(ok: bool, citation: Citation | None) -> str:
    if not ok:
        return "fail"
    return "pass" if citation is not None and citation.verified else "assumed"


def check_zoning(
    parcel: ParcelSpec,
    params: ZoningParams,
    *,
    footprint: list[tuple[float, float]] | None = None,
    footprints: list[list[tuple[float, float]]] | None = None,
    floors: int | None = None,
    floor_height_m: float | None = None,
    rules: dict[str, Rule] | None = None,
) -> ZoningReport:
    parcel_area = parcel.area_tapu_m2 or parcel.area_computed_m2
    buildable = buildable_polygon(parcel, params.setbacks)
    checks: list[Check] = []
    cit_sb = _citation(params, "setbacks")

    checks.append(Check(
        id="Z-BUILDABLE",
        status=_status(buildable.area > 1.0, cit_sb),
        actual=round(buildable.area, 3), limit=1.0,
        message=f"buildable area after setbacks: {buildable.area:.2f} m2",
        citation=cit_sb))

    limits: dict[str, float | None] = {
        "taks_area_m2": params.taks * parcel_area,
        "kaks_area_m2": params.kaks * parcel_area,
        "hmax_m": params.hmax_m,
    }

    fps = footprints if footprints is not None else ([footprint] if footprint is not None else None)
    if fps is not None:
        fp = unary_union([Polygon(f) for f in fps])
        inside = fp.difference(buildable.buffer(EPS)).area < EPS
        checks.append(Check(
            id="Z-SETBACK-FIT", status=_status(inside, cit_sb),
            actual=round(fp.area, 3), limit=round(buildable.area, 3),
            message="footprint lies inside the setback-reduced area"
                    if inside else "footprint extends into a setback zone",
            citation=cit_sb))
        cit = _citation(params, "taks")
        checks.append(Check(
            id="Z-TAKS", status=_status(fp.area <= limits["taks_area_m2"] + EPS, cit),
            actual=round(fp.area, 3), limit=round(limits["taks_area_m2"], 3),
            message=f"footprint {fp.area:.2f} m2 vs TAKS {params.taks} x {parcel_area:.2f} m2",
            citation=cit))
        if floors is not None:
            gross = fp.area * floors
            cit = _citation(params, "kaks")
            checks.append(Check(
                id="Z-KAKS", status=_status(gross <= limits["kaks_area_m2"] + EPS, cit),
                actual=round(gross, 3), limit=round(limits["kaks_area_m2"], 3),
                message=f"gross {gross:.2f} m2 (all floors counted) vs KAKS {params.kaks}",
                citation=cit))

    if floors is not None and params.kat_adedi_max is not None:
        cit = _citation(params, "kat_adedi_max")
        checks.append(Check(
            id="Z-KAT", status=_status(floors <= params.kat_adedi_max, cit),
            actual=float(floors), limit=float(params.kat_adedi_max),
            message=f"{floors} floors vs max {params.kat_adedi_max}", citation=cit))

    if floors is not None and floor_height_m is not None and params.hmax_m is not None:
        h = floors * floor_height_m
        cit = _citation(params, "hmax_m")
        checks.append(Check(
            id="Z-HMAX", status=_status(h <= params.hmax_m + EPS, cit),
            actual=round(h, 3), limit=params.hmax_m,
            message=f"building height {h:.2f} m vs Hmax {params.hmax_m} m", citation=cit))

    if rules:
        checks.extend(check_setback_defaults(params, rules))
        if floor_height_m is not None:
            rule = rules["PAIY-M28-KAT-YUKSEKLIK"]
            checks.append(Check(
                id="Z-PAIY-M28-KAT-YUKSEKLIK",
                status="pass" if rule.holds(floor_height_m) else "fail",
                actual=floor_height_m, limit=float(rule.value),  # type: ignore[arg-type]
                message=rule.summary, citation=rule.citation()))

    ring = list(buildable.exterior.coords)[:-1] if not buildable.is_empty else []
    return ZoningReport(
        parcel_id=parcel.parcel_id,
        demo_assumption=params.source_doc.type == "demo_assumption",
        buildable_polygon=[(round(x, 4), round(y, 4)) for x, y in ring],
        buildable_area_m2=round(buildable.area, 4),
        limits={k: (None if v is None else round(v, 4)) for k, v in limits.items()},
        checks=checks,
        verdict="fail" if any(c.status == "fail" for c in checks) else "pass",
    )
