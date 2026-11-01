"""Parcel loading, normalisation, validation and edge-role assignment."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml
from shapely.geometry import Polygon

from .crs import LocalFrame
from .schemas import (
    Adjacent,
    Admin,
    CrsInfo,
    Edge,
    EdgeRole,
    ParcelSource,
    ParcelSpec,
    Pt,
    ValidationIssue,
)

DUP_TOL_M = 0.01      # consecutive points closer than this are merged
MIN_EDGE_M = 0.30     # shorter edges are reported as a warning
AREA_TOL = 0.01       # tapu vs computed area, relative


def signed_area(ring: list[Pt]) -> float:
    s = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        s += x1 * y2 - x2 * y1
    return s / 2.0


def clean_ring(ring: list[Pt]) -> list[Pt]:
    """Drop the closing duplicate and near-duplicate consecutive points; make it CCW."""
    pts = [tuple(p) for p in ring]
    if len(pts) > 1 and math.dist(pts[0], pts[-1]) < DUP_TOL_M:
        pts = pts[:-1]
    out: list[Pt] = []
    for p in pts:
        if not out or math.dist(out[-1], p) >= DUP_TOL_M:
            out.append(p)
    if len(out) > 1 and math.dist(out[0], out[-1]) < DUP_TOL_M:
        out.pop()
    if signed_area(out) < 0:
        out.reverse()
    return out


def build_edges(ring: list[Pt]) -> list[Edge]:
    return [
        Edge(i=i, a=a, b=b, length=math.dist(a, b))
        for i, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1]))
    ]


def parcel_from_local_ring(
    parcel_id: str,
    ring: list[Pt],
    *,
    source: ParcelSource,
    admin: Admin | None = None,
    crs: CrsInfo | None = None,
    area_tapu_m2: float | None = None,
) -> ParcelSpec:
    ring = clean_ring(ring)
    return ParcelSpec(
        parcel_id=parcel_id,
        source=source,
        admin=admin,
        crs=crs,
        ring_local=ring,
        area_tapu_m2=area_tapu_m2,
        area_computed_m2=abs(signed_area(ring)),
        edges=build_edges(ring),
    )


def parcel_from_geojson(
    feature: dict[str, Any],
    parcel_id: str,
    *,
    source: ParcelSource,
    admin: Admin | None = None,
    area_tapu_m2: float | None = None,
) -> ParcelSpec:
    """TKGM-style GeoJSON Feature: Polygon in [lon, lat] (WGS84, verified by value range)."""
    if feature.get("type") != "Feature" or feature["geometry"]["type"] != "Polygon":
        raise ValueError("expected a GeoJSON Feature with Polygon geometry")
    lonlat = [tuple(c[:2]) for c in feature["geometry"]["coordinates"][0]]
    lon0 = sum(p[0] for p in lonlat) / len(lonlat)
    lat0 = sum(p[1] for p in lonlat) / len(lonlat)
    if not (25 <= lon0 <= 45 and 35 <= lat0 <= 43):
        raise ValueError(f"coordinates ({lon0:.4f}, {lat0:.4f}) are not WGS84 lon/lat in Turkey")
    frame = LocalFrame.at((lon0, lat0))
    ring = [frame.to_local(lon, lat) for lon, lat in lonlat]
    crs = CrsInfo(
        input="EPSG:4326",
        projected=f"EPSG:{frame.epsg}",
        local_origin_lonlat=(lon0, lat0),
    )
    return parcel_from_local_ring(
        parcel_id, ring, source=source, admin=admin, crs=crs, area_tapu_m2=area_tapu_m2
    )


def validate_parcel(parcel: ParcelSpec) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    poly = Polygon(parcel.ring_local)
    if not poly.is_valid:
        issues.append(ValidationIssue(level="error", code="P-INVALID",
                                      message="ring is not a simple polygon (self-intersection)"))
    if parcel.area_tapu_m2:
        diff = abs(parcel.area_computed_m2 - parcel.area_tapu_m2) / parcel.area_tapu_m2
        if diff > AREA_TOL:
            issues.append(ValidationIssue(
                level="warn", code="P-AREA",
                message=f"computed area {parcel.area_computed_m2:.2f} m2 differs from tapu "
                        f"{parcel.area_tapu_m2:.2f} m2 by {diff:.1%}"))
    for e in parcel.edges:
        if e.length < MIN_EDGE_M:
            issues.append(ValidationIssue(level="warn", code="P-MICRO-EDGE",
                                          message=f"edge {e.i} is only {e.length:.3f} m"))
    roles = [e.role for e in parcel.edges]
    if EdgeRole.FRONT not in roles:
        issues.append(ValidationIssue(level="error", code="P-NO-FRONT",
                                      message="no edge has role 'front'"))
    if EdgeRole.UNKNOWN in roles:
        issues.append(ValidationIssue(level="error", code="P-ROLE-UNKNOWN",
                                      message="some edges still have role 'unknown'"))
    return issues


def assign_roles(parcel: ParcelSpec, roles: dict[int, dict[str, Any]]) -> ParcelSpec:
    """roles: {edge_index: {role, adjacent?, road_name?, road_width_m?}}"""
    edges = []
    for e in parcel.edges:
        r = roles.get(e.i)
        if r is None:
            edges.append(e)
            continue
        edges.append(e.model_copy(update={
            "role": EdgeRole(r["role"]),
            "adjacent": Adjacent(r.get("adjacent", "unknown")),
            "road_name": r.get("road_name"),
            "road_width_m": r.get("road_width_m"),
        }))
    unknown_idx = set(roles) - {e.i for e in parcel.edges}
    if unknown_idx:
        raise ValueError(f"role given for non-existent edges: {sorted(unknown_idx)}")
    return parcel.model_copy(update={"edges": edges})


def load_edge_roles(path: str | Path) -> dict[int, dict[str, Any]]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return {int(k): v for k, v in data["edges"].items()}
