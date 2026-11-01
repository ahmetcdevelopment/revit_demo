"""Deterministic compiler: BuildingSpec -> ordered Op list (the only thing a backend executes)."""

from __future__ import annotations

import math

from shapely.geometry import Point, Polygon

from .schemas import BuildingSpec, Op


def compile_spec(spec: BuildingSpec) -> list[Op]:
    ops: list[Op] = []
    emitted: set[str] = set()

    def add(op: str, ref: str, deps: list[str], args: dict) -> None:
        for d in deps:
            if d not in emitted:
                raise ValueError(f"op for {ref} depends on {d}, which is not emitted before it")
        ops.append(Op(op_id=f"{len(ops) + 1:04d}", op=op, spec_ref=ref, depends_on=deps, args=args))
        emitted.add(ref)

    for lv in spec.levels:
        add("create_level", lv.id, [], {"name": lv.name, "elevation": lv.elevation,
                                        "height": lv.height})
    slab_for = {(s.level, s.id.split("-")[-1]): s for s in spec.slabs}   # (level, block) -> slab
    for lv in spec.levels:
        for w in (w for w in spec.walls if w.level == lv.id):
            add("create_wall", w.id, [lv.id],
                {"level": w.level, "a": w.a, "b": w.b, "thickness": w.thickness,
                 "height": w.height, "type": w.type})
        for s in (s for s in spec.slabs if s.level == lv.id):
            add("create_floor", s.id, [lv.id],
                {"level": s.level, "outline": s.outline, "openings": s.openings,
                 "thickness": s.thickness})
    for st in spec.stairs:
        blk = st.id.split("-")[1]
        add("create_stair", st.id, [st.from_level, st.to_level, slab_for[(st.to_level, blk)].id],
            st.model_dump(exclude={"id"}))
    top = spec.levels[-1]
    for roof in spec.roofs:
        add("create_roof", roof.id, [top.id], {"level": top.id, **roof.model_dump(exclude={"id"})})
    for lv in spec.levels:
        for r in (r for r in spec.rooms if r.level == lv.id):
            add("create_room", r.id, [lv.id],
                {"level": r.level, "name": r.name, "type": r.type, "unit": r.unit,
                 "outline": r.outline, "kitchen_niche": r.kitchen_niche,
                 "ventilation": r.ventilation})
    for r in spec.rooms:
        add("tag_room", f"TAG-{r.id}", [r.id], {"room": r.id, "level": r.level, "outline": r.outline})
    for o in spec.openings:
        add("place_door" if o.kind == "door" else "place_window", o.id, [o.host_wall],
            {"level": o.level, "host_wall": o.host_wall, "at": o.at, "width": o.width,
             "height": o.height, "sill": o.sill, "family_hint": o.family_hint, "role": o.role})
    hosted: dict[str, list] = {}
    hosted_ids: dict[str, list[str]] = {}
    for o in spec.openings:
        hosted.setdefault(o.host_wall, []).append(
            {"at": o.at, "width": o.width, "height": o.height, "sill": o.sill})
        hosted_ids.setdefault(o.host_wall, []).append(o.id)
    footprints = [Polygon(f) for f in spec.footprints]
    for w in spec.walls:
        if w.type == "ext_brick" and w.facade in ("front", "rear", "side"):
            f = getattr(spec.facade, "front" if w.facade == "side" else w.facade)
            add("create_brick_panel", f"BP-{w.id}", [w.id, *hosted_ids.get(w.id, [])],
                {"wall": w.id, "level": w.level, "a": w.a, "b": w.b, "thickness": w.thickness,
                 "height": w.height, "bond": f.bond, "brick": f.brick.model_dump(),
                 "color": f.color, "normal": _outward(w, footprints), "openings": hosted.get(w.id, [])})
    return ops


def _outward(w, footprints: list[Polygon]) -> list[float]:
    """Unit normal of the wall pointing out of the building (away from the footprint it belongs to)."""
    dx, dy = w.b[0] - w.a[0], w.b[1] - w.a[1]
    n = math.hypot(dx, dy)
    nx, ny = dy / n, -dx / n
    probe = Point((w.a[0] + w.b[0]) / 2 + nx * 0.4, (w.a[1] + w.b[1]) / 2 + ny * 0.4)
    if any(f.contains(probe) for f in footprints):
        nx, ny = -nx, -ny
    return [round(nx, 6), round(ny, 6)]
