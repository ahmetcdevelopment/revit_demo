"""validate_spec: structural integrity, geometry, circulation graph, PAİY and zoning checks.

Runs entirely offline (no Revit). Errors block `build_in_revit`; warnings are reported.
"""

from __future__ import annotations

from collections import defaultdict, deque

from pydantic import BaseModel, ConfigDict
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from .rules import Rule
from .schemas import (
    BuildingSpec,
    ParcelSpec,
    ValidationIssue,
    ZoningParams,
    ZoningReport,
)
from .zoning import check_zoning

TOL = 1e-3
OUTSIDE = "OUTSIDE"

# room type -> (area rule, short-side rule) in the PAİY catalogue (Madde 29)
ROOM_RULES = {
    "living": ("PAIY-M29-SALON-ALAN", "PAIY-M29-SALON-KENAR"),
    "bedroom": ("PAIY-M29-YATAK-ALAN", "PAIY-M29-YATAK-KENAR"),
    "kitchen": ("PAIY-M29-MUTFAK-ALAN", "PAIY-M29-MUTFAK-KENAR"),
    "bath": ("PAIY-M29-BANYO-ALAN", "PAIY-M29-BANYO-KENAR"),
    "wc": ("PAIY-M29-WC-ALAN", "PAIY-M29-WC-KENAR"),
    "hall": (None, "PAIY-M29-HOL"),
}


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    issues: list[ValidationIssue]
    zoning: ZoningReport | None = None

    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "error"]


def min_width_ok(poly: Polygon, width: float) -> bool:
    """True if a disc of diameter `width` fits everywhere along the room (works for L-shapes)."""
    return not poly.buffer(-(width / 2) + 1e-4).is_empty


def stack_key(room_id: str) -> str:
    """'R-L1-B1-A-SALON' -> 'B1-A-SALON' (the same room on every level)."""
    return "-".join(room_id.split("-")[2:])


def validate_spec(
    spec: BuildingSpec,
    *,
    parcel: ParcelSpec | None = None,
    params: ZoningParams | None = None,
    rules: dict[str, Rule] | None = None,
) -> ValidationResult:
    issues: list[ValidationIssue] = []

    def err(code: str, msg: str) -> None:
        issues.append(ValidationIssue(level="error", code=code, message=msg))

    def warn(code: str, msg: str) -> None:
        issues.append(ValidationIssue(level="warn", code=code, message=msg))

    levels = {lv.id: lv for lv in spec.levels}
    walls = {w.id: w for w in spec.walls}

    # --- ids
    all_ids = ([lv.id for lv in spec.levels] + [w.id for w in spec.walls]
               + [s.id for s in spec.slabs] + [s.id for s in spec.stairs]
               + [r.id for r in spec.rooms] + [o.id for o in spec.openings]
               + [r.id for r in spec.roofs])
    dup = {i for i in all_ids if all_ids.count(i) > 1}
    if dup:
        err("S-DUP-ID", f"duplicate ids: {sorted(dup)}")

    # --- references
    for w in spec.walls:
        if w.level not in levels:
            err("S-REF-LEVEL", f"wall {w.id} -> unknown level {w.level}")
    for coll, items in (("slab", spec.slabs), ("room", spec.rooms), ("opening", spec.openings)):
        for it in items:
            if it.level not in levels:
                err("S-REF-LEVEL", f"{coll} {it.id} -> unknown level {it.level}")
    for st in spec.stairs:
        for lv in (st.from_level, st.to_level):
            if lv not in levels:
                err("S-REF-LEVEL", f"stair {st.id} -> unknown level {lv}")

    # --- openings sit on their host wall
    for o in spec.openings:
        w = walls.get(o.host_wall)
        if w is None:
            err("S-REF-WALL", f"opening {o.id} -> unknown wall {o.host_wall}")
            continue
        if w.level != o.level:
            err("S-WALL-LEVEL", f"opening {o.id} level {o.level} != wall level {w.level}")
        line = LineString([w.a, w.b])
        if line.distance(Point(o.at)) > TOL:
            err("S-OPENING-OFF-WALL", f"opening {o.id} is {line.distance(Point(o.at)):.3f} m off its wall")
        else:
            t = line.project(Point(o.at))
            if t - o.width / 2 < -TOL or t + o.width / 2 > line.length + TOL:
                err("S-OPENING-EXTENT", f"opening {o.id} sticks out of wall {w.id}")
        if w.type == "party":
            err("S-PARTY-OPENING", f"opening {o.id} is in party wall {w.id}")
    # openings on one wall must not overlap each other
    by_wall: dict[str, list] = defaultdict(list)
    for o in spec.openings:
        if o.host_wall in walls:
            by_wall[o.host_wall].append((LineString([walls[o.host_wall].a, walls[o.host_wall].b])
                                         .project(Point(o.at)), o))
    for wid, items in by_wall.items():
        items.sort(key=lambda x: x[0])
        for (t1, o1), (t2, o2) in zip(items, items[1:]):
            if t2 - o2.width / 2 < t1 + o1.width / 2 - TOL:
                err("S-OPENING-OVERLAP", f"openings {o1.id} and {o2.id} overlap on {wid}")

    # --- rooms: inside footprints, no overlaps
    fp = unary_union([Polygon(f) for f in spec.footprints])
    by_level: dict[str, list] = defaultdict(list)
    for r in spec.rooms:
        poly = Polygon(r.outline)
        if not poly.is_valid:
            err("R-INVALID", f"room {r.id} polygon is invalid")
        if poly.difference(fp.buffer(TOL)).area > 1e-6:
            err("R-OUTSIDE", f"room {r.id} extends outside the footprint")
        by_level[r.level].append((r, poly))
    for lv, items in by_level.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if items[i][1].intersection(items[j][1]).area > 1e-6:
                    err("R-OVERLAP", f"rooms {items[i][0].id} and {items[j][0].id} overlap")
        cover = sum(p.area for _, p in items) / fp.area
        if cover < 0.75:
            warn("R-COVERAGE", f"rooms cover only {cover:.0%} of the footprint on {lv}")

    # --- stacked rooms keep their outline on every level
    shapes: dict[str, set[tuple]] = defaultdict(set)
    for r in spec.rooms:
        shapes[stack_key(r.id)].add(tuple(r.outline))
    for key, s in shapes.items():
        if len(s) > 1:
            err("R-STACK", f"room '{key}' outline differs between levels")

    # --- circulation graph
    graph: dict[str, set[str]] = defaultdict(set)

    def link(a: str, b: str) -> None:
        graph[a].add(b)
        graph[b].add(a)

    polys = {r.id: Polygon(r.outline) for r in spec.rooms}
    for r in spec.rooms:
        graph[r.id]  # ensure node
    for o in spec.openings:
        if o.kind != "door":
            continue
        near = [r.id for r in spec.rooms
                if r.level == o.level and polys[r.id].distance(Point(o.at)) <= 0.3]
        if o.role in ("main_entry", "rear_exit"):
            near.append(OUTSIDE)
        if len(near) < 2:
            err("C-DOOR-DANGLING", f"door {o.id} connects fewer than two spaces ({near})")
        for a in near:
            for b in near:
                if a < b:
                    link(a, b)
    for lv, items in by_level.items():    # open core spaces share an open boundary
        core = [r for r, _ in items if r.type in ("core_hall", "stair")]
        for a in core:
            for b in core:
                if a.id < b.id and polys[a.id].distance(polys[b.id]) < 1e-6:
                    link(a.id, b.id)
    for st in spec.stairs:
        blk = st.id.split("-")[1]
        lo = [r.id for r in spec.rooms if r.level == st.from_level and r.type == "stair"
              and f"-{blk}-" in r.id]
        hi = [r.id for r in spec.rooms if r.level == st.to_level and r.type == "stair"
              and f"-{blk}-" in r.id]
        for a in lo:
            for b in hi:
                link(a, b)
    seen = {OUTSIDE}
    queue = deque([OUTSIDE])
    while queue:
        for nb in graph[queue.popleft()]:
            if nb not in seen:
                seen.add(nb)
                queue.append(nb)
    unreachable = [r.id for r in spec.rooms if r.id not in seen]
    if unreachable:
        err("C-UNREACHABLE", f"rooms not reachable from outside: {unreachable}")

    # --- stairs
    for st in spec.stairs:
        lo, hi = levels.get(st.from_level), levels.get(st.to_level)
        if lo and hi and abs(sum(st.risers) * st.riser_h - (hi.elevation - lo.elevation)) > TOL:
            err("T-HEIGHT", f"stair {st.id}: risers do not add up to the storey height")
        if rules:
            for rid, val in (("PAIY-M31-KOL", st.run_width), ("PAIY-M31-BASAMAK", st.tread_d),
                             ("PAIY-M31-2AB", (2 * st.riser_h + st.tread_d) * 100)):
                if not rules[rid].holds(val):
                    err("T-" + rid, f"stair {st.id}: {rules[rid].summary} (got {val:.3f})")
            if st.riser_h > 0.16 + 1e-9:
                err("T-PAIY-M31-RIHT", f"stair {st.id}: riser {st.riser_h} m > 0.16 m")

    # --- PAİY room minimums (Madde 29, 30, 32)
    if rules:
        for r in spec.rooms:
            poly = polys[r.id]
            if r.type in ROOM_RULES:
                area_id, side_id = ROOM_RULES[r.type]
                if area_id:
                    need = rules[area_id].value
                    if r.kitchen_niche:
                        need += rules["PAIY-M29-MUTFAK-ALAN"].value
                    if poly.area + 1e-6 < need:
                        err("M-AREA", f"{r.id} {poly.area:.2f} m2 < {need:.2f} m2 ({rules[area_id].article})")
                if side_id and not min_width_ok(poly, rules[side_id].value):
                    err("M-SHORT", f"{r.id} narrower than {rules[side_id].value} m ({rules[side_id].article})")
                if r.type in ("bedroom", "living") and r.ventilation != "natural":
                    err("M-LIGHT", f"{r.id} needs natural light/ventilation (Madde 32(1))")
            if r.type == "core_hall" and r.name.startswith("Giri") and \
                    not min_width_ok(poly, rules["PAIY-M30-GIRIS"].value):
                err("M-ENTRY", f"{r.id} entry corridor narrower than {rules['PAIY-M30-GIRIS'].value} m")
        for lv in spec.levels:
            if lv.id != "R" and not rules["PAIY-M28-KAT-YUKSEKLIK"].holds(lv.height):
                err("L-HEIGHT", f"level {lv.id} height {lv.height} m exceeds PAİY Madde 28(1)(c)")
        # bedrooms and living rooms need a window on the facade (Madde 32(1))
        win_hosts: dict[tuple[str, str], int] = defaultdict(int)
        for o in spec.openings:
            if o.kind == "window":
                for r in spec.rooms:
                    if r.level == o.level and polys[r.id].distance(Point(o.at)) <= 0.3:
                        win_hosts[(r.level, r.id)] += 1
        for r in spec.rooms:
            if r.type in ("bedroom", "living") and win_hosts[(r.level, r.id)] == 0:
                err("M-NO-WINDOW", f"{r.id} has no window (Madde 32(1))")
        # several blocks: Madde 24(2)
        if len(spec.footprints) > 1:
            polys_fp = [Polygon(f) for f in spec.footprints]
            for i in range(len(polys_fp)):
                for j in range(i + 1, len(polys_fp)):
                    gap = polys_fp[i].distance(polys_fp[j])
                    if not rules["PAIY-M24-BLOK-ARASI"].holds(gap):
                        err("B-GAP", f"blocks {i + 1} and {j + 1} are {gap:.2f} m apart "
                                     f"({rules['PAIY-M24-BLOK-ARASI'].article})")

    # --- zoning
    zoning = None
    if parcel is not None and params is not None:
        n_floors = len([lv for lv in spec.levels if lv.id != "R"])
        zoning = check_zoning(parcel, params, footprints=spec.footprints, floors=n_floors,
                              floor_height_m=spec.levels[0].height, rules=rules)
        for c in zoning.checks:
            if c.status == "fail":
                err(c.id, c.message)

    return ValidationResult(ok=not any(i.level == "error" for i in issues), issues=issues,
                            zoning=zoning)
