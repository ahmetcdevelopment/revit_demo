"""Rule-based planner v2: parcel + zoning -> BuildingSpec.

Typology: one bitişik-nizam block (core + two flats per floor) per road end of the parcel.
Several blocks on one parcel keep PAİY Madde 24(2) distance (sum of both approach distances).
Layout rationale and dimensions: docs/03-domain/04-kat-plani-tasarimi.md.
Deterministic: same inputs always give the same spec (and the same spec_id).
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from .schemas import (
    BlockInfo,
    BuildingSpec,
    Derived,
    EdgeRole,
    Level,
    Opening,
    ParcelSpec,
    Project,
    Pt,
    Roof,
    Room,
    Slab,
    Stair,
    Wall,
    ZoningParams,
)
from .zoning import buildable_polygon

TE, TC, TI = 0.25, 0.20, 0.10           # exterior/party, core, partition wall thickness (m)
RUN_W, WELL, HOL_W, HOLH_D = 1.20, 0.10, 1.20, 1.30
CORE_W = 2 * RUN_W + WELL
WET_W, BANYO_D, WC_D, BED1_W = 2.20, 1.90, 1.30, 2.60
SLAB_T, PARAPET, MODULE = 0.20, 0.60, 0.05
RISER_MAX, LANDING = 0.16, 1.30          # no lift (PAİY Madde 31(2)(a))
MIN_BLOCK_W, MIN_BLOCK_D, MAX_BLOCK_D = 16.6, 11.8, 14.0   # width: flat >= 6.6 m (wet 2.2 + hol 1.2 + bed 3.0)
SEARCH_WINDOW = 4.0                      # m: look this far past the first valid position for a wider fit
BLOCK_GAP_MIN = 6.0                      # Madde 24(2): 3.00 + 3.00 (Madde 23(1)(b)(c))
PARTY_TOL = 0.6                          # footprint side counts as party if this close to the boundary

Rect = tuple[float, float, float, float]  # u0, u1, v0, v1 (block-local, net)


class PlanningError(ValueError):
    pass


def _floor_mod(x: float) -> float:
    return math.floor(x / MODULE + 1e-9) * MODULE


def _ceil_mod(x: float) -> float:
    return math.ceil(x / MODULE - 1e-9) * MODULE


def _r(p: tuple[float, float]) -> Pt:
    return (round(float(p[0]), 4), round(float(p[1]), 4))


def _ccw(ring: list[Pt]) -> list[Pt]:
    s = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]))
    return list(reversed(ring)) if s < 0 else ring


# ----------------------------------------------------------------------------- axis frame
def axis_angle(parcel: ParcelSpec) -> float:
    """Direction (rad) of the party boundaries; fallback: long side of the minimum rectangle."""
    sx = sy = 0.0
    for e in parcel.edges:
        if e.role == EdgeRole.SIDE_PARTY:
            dx, dy = e.b[0] - e.a[0], e.b[1] - e.a[1]
            if dx < -1e-9 or (abs(dx) <= 1e-9 and dy < 0):
                dx, dy = -dx, -dy
            sx, sy = sx + dx, sy + dy
    if sx == 0 and sy == 0:
        c = list(Polygon(parcel.ring_local).minimum_rotated_rectangle.exterior.coords)
        e1, e2 = (c[1][0] - c[0][0], c[1][1] - c[0][1]), (c[2][0] - c[1][0], c[2][1] - c[1][1])
        sx, sy = e1 if math.hypot(*e1) >= math.hypot(*e2) else e2
        if sx < 0:
            sx, sy = -sx, -sy
    return math.atan2(sy, sx)


def to_axis(p: tuple[float, float], a: float) -> tuple[float, float]:
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c + p[1] * s, -p[0] * s + p[1] * c)


def from_axis(p: tuple[float, float], a: float) -> tuple[float, float]:
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def road_ends(parcel: ParcelSpec, a: float, mid_x: float) -> list[str]:
    """Which ends ('min'/'max' along the axis) have a road edge."""
    ends = set()
    for e in parcel.edges:
        if e.role == EdgeRole.FRONT:
            cx = to_axis(((e.a[0] + e.b[0]) / 2, (e.a[1] + e.b[1]) / 2), a)[0]
            ends.add("min" if cx < mid_x else "max")
    return [x for x in ("min", "max") if x in ends]


# ----------------------------------------------------------------------------- block fit
def fit_block(b_ax: Polygon, end: str, depth: float) -> tuple[float, float, float, float] | None:
    """First axis-aligned rectangle of `depth` along the axis from the given end that fits."""
    minx, miny, maxx, maxy = b_ax.bounds
    vertex_x = sorted({round(x, 6) for x, _ in b_ax.exterior.coords})
    best: tuple[float, float, float, float] | None = None
    first_offset: float | None = None
    for k in range(int((maxx - minx - depth) / 0.05)):
        offset = k * 0.05
        if first_offset is not None and offset > first_offset + SEARCH_WINDOW:
            break
        x0 = minx + offset if end == "min" else maxx - depth - offset
        x1 = x0 + depth
        xs = list(np.linspace(x0, x1, 13)) + [v for v in vertex_x if x0 < v < x1]
        lo, hi = -math.inf, math.inf
        for x in xs:
            hit = LineString([(x, miny - 1), (x, maxy + 1)]).intersection(b_ax)
            if hit.is_empty:
                lo, hi = 1.0, 0.0
                break
            lo, hi = max(lo, hit.bounds[1]), min(hi, hit.bounds[3])
        if hi - lo < MIN_BLOCK_W:
            continue
        ylo, yhi = _ceil_mod(lo), _floor_mod(hi)
        if not b_ax.buffer(1e-6).contains(box(x0, ylo, x1, yhi)):
            continue
        if first_offset is None:
            first_offset = offset
        if best is None or (yhi - ylo) > (best[3] - best[2]) + 1e-9:
            best = (x0, x1, ylo, yhi)
    return best


def stair_numbers(height: float) -> tuple[list[int], float, float, float]:
    """risers per run, riser height, tread depth, zone length. PAİY Madde 31(2)."""
    n = math.ceil(height / RISER_MAX - 1e-9)
    r = height / n
    b = round(0.62 - 2 * r, 2)
    if not (0.27 <= b and 0.60 <= 2 * r + b <= 0.64):
        raise PlanningError(f"no valid tread for riser {r:.4f}")
    n1 = math.ceil(n / 2)
    return [n1, n - n1], round(r, 5), b, round((n1 - 1) * b + LANDING, 4)


# ----------------------------------------------------------------------------- block layout
@dataclass
class Tile:
    key: str
    name: str
    type: str
    unit: str | None
    rects: list[Rect]
    vent: str = "natural"


CORE_TYPES = ("core_hall", "stair")
MIN_WALL_LEN_M = 0.25


def _mirror(r: Rect, w: float) -> Rect:
    return (w - r[1], w - r[0], r[2], r[3])


def block_tiles(w: float, d: float, height: float) -> tuple[list[Tile], dict]:
    """Net room rectangles of one block, in block-local (u across, v from the facade)."""
    _, _, _, zone = stair_numbers(height)
    wn = (w - 2 * TE - 2 * TC - CORE_W) / 2
    bed2_w = wn - WET_W - HOL_W - 2 * TI
    ws = wn - BED1_W - TI
    if bed2_w < 3.0 or ws < 3.5:
        raise PlanningError(f"block width {w:.2f} m too narrow for the flat layout (flat {wn:.2f} m)")
    ds = None
    for k in range(int((6.0 - 4.4) / MODULE) + 1):
        cand = 6.0 - k * MODULE
        vh1 = TE + cand + TI + HOLH_D
        v_s = vh1 + 0.15
        v3 = vh1 + TI
        rear_corridor = (d - TE) - (v_s + zone)
        kitchen_d = (d - TE) - (v3 + BANYO_D + TI + WC_D + TI)
        if rear_corridor >= 1.2 and kitchen_d >= 1.8:
            ds = cand
            break
    if ds is None:
        raise PlanningError(f"block depth {d:.2f} m too small for core + flat rows")
    xl, xr = TE, TE + wn
    ua, ub = xr + TC, xr + TC + CORE_W
    vh0, vh1 = TE + ds + TI, TE + ds + TI + HOLH_D
    v3 = vh1 + TI
    v_s = vh1 + 0.15
    hv0 = xl + WET_W + TI
    hv1 = hv0 + HOL_W
    yb = v3 + BANYO_D + TI
    ym = yb + WC_D + TI
    flat: list[tuple[str, str, str, list[Rect], str]] = [
        ("SALON", "Salon", "living", [(xl, xl + ws, TE, TE + ds)], "natural"),
        ("BED1", "Yatak Odası 1", "bedroom", [(xl + ws + TI, xr, TE, TE + ds)], "natural"),
        ("HOL", "Hol", "hall", [(xl, xr, vh0, vh1), (hv0, hv1, vh1, d - TE)], "natural"),
        ("BANYO", "Banyo", "bath", [(xl, xl + WET_W, v3, v3 + BANYO_D)], "mechanical"),
        ("WC", "WC", "wc", [(xl, xl + WET_W, yb, yb + WC_D)], "mechanical"),
        ("MUTFAK", "Mutfak", "kitchen", [(xl, xl + WET_W, ym, d - TE)], "natural"),
        ("BED2", "Yatak Odası 2", "bedroom", [(hv1 + TI, xr, v3, d - TE)], "natural"),
    ]
    tiles: list[Tile] = []
    for side in ("A", "B"):
        for key, name, typ, rects, vent in flat:
            rr = [_mirror(r, w) if side == "B" else r for r in rects]
            tiles.append(Tile(f"{side}-{key}", name, typ, side, rr, vent))
    tiles.append(Tile("CORE-LOBBY", "Giriş Holü", "core_hall", None, [(ua, ub, TE, v_s)]))
    tiles.append(Tile("CORE-STAIR", "Merdiven", "stair", None, [(ua, ub, v_s, v_s + zone)]))
    tiles.append(Tile("CORE-REAR", "Arka Çıkış", "core_hall", None, [(ua, ub, v_s + zone, d - TE)]))
    geo = {"ua": ua, "ub": ub, "vS": v_s, "zone": zone, "wn": wn, "ds": ds}
    return tiles, geo


@dataclass
class WallSeg:
    pair: tuple[str, str]
    a: tuple[float, float]
    b: tuple[float, float]
    thickness: float
    type: str


def interior_walls(tiles: list[Tile]) -> list[WallSeg]:
    """Walls = the gaps between rectangles of different tiles (thickness = gap)."""
    segs: list[WallSeg] = []
    for i, t1 in enumerate(tiles):
        for t2 in tiles[i + 1:]:
            core = t1.type in CORE_TYPES and t2.type in CORE_TYPES
            for r1 in t1.rects:
                for r2 in t2.rects:
                    for horiz in (True, False):  # gap along u (vertical wall) / along v
                        a0, a1, b0, b1 = (r1[0], r1[1], r2[0], r2[1]) if horiz else (r1[2], r1[3], r2[2], r2[3])
                        o0, o1, p0, p1 = (r1[2], r1[3], r2[2], r2[3]) if horiz else (r1[0], r1[1], r2[0], r2[1])
                        lo, hi = max(o0, p0), min(o1, p1)
                        if hi - lo < 1e-6:
                            continue
                        for first, second, (e1, s2) in ((r1, r2, (a1, b0)), (r2, r1, (b1, a0))):
                            gap = round(s2 - e1, 6)
                            if gap < -1e-6 or gap > 0.5:
                                continue
                            if abs(gap) < 1e-6:
                                if core:
                                    continue
                                raise PlanningError(f"tiles {t1.key}/{t2.key} touch without a wall")
                            mid = (e1 + s2) / 2
                            typ = "core" if (t1.type in CORE_TYPES or t2.type in CORE_TYPES) else "partition"
                            a, b = ((mid, lo), (mid, hi)) if horiz else ((lo, mid), (hi, mid))
                            segs.append(WallSeg(tuple(sorted((t1.key, t2.key))), a, b, gap, typ))
                            break
    merged: list[WallSeg] = []
    for s in sorted(segs, key=lambda s: (s.pair, s.a, s.b)):
        for m in merged:
            same_line = m.pair == s.pair and math.isclose(m.thickness, s.thickness)
            if same_line and (m.b == s.a or m.a == s.b) and \
               (math.isclose(m.a[0], s.a[0]) and math.isclose(m.b[0], s.b[0]) or
                    math.isclose(m.a[1], s.a[1]) and math.isclose(m.b[1], s.b[1])):
                m.a, m.b = min(m.a, s.a), max(m.b, s.b)
                break
        else:
            merged.append(s)
    # A contact shorter than the wall is thick is only a corner notch between two rooms, already covered
    # by the end caps of the perpendicular walls. Revit also drops such stubs silently (found by verify_model).
    return [s for s in merged if math.dist(s.a, s.b) >= MIN_WALL_LEN_M]


def _hash_spec(spec: BuildingSpec) -> str:
    return hashlib.sha256(spec.model_dump_json(exclude={"spec_id"}).encode("utf-8")).hexdigest()[:12]


# ----------------------------------------------------------------------------- planning
def plan_building(
    parcel: ParcelSpec,
    params: ZoningParams,
    *,
    floors: int = 3,
    floor_height: float = 3.0,
    ends: list[str] | None = None,
) -> BuildingSpec:
    angle = axis_angle(parcel)
    buildable = buildable_polygon(parcel, params.setbacks)
    if buildable.is_empty:
        raise PlanningError("setbacks leave no buildable area")

    def to_ax_poly(a: float) -> Polygon:
        return Polygon([to_axis(p, a) for p in buildable.exterior.coords])

    b_ax = to_ax_poly(angle)
    mid_x = (b_ax.bounds[0] + b_ax.bounds[2]) / 2
    available = road_ends(parcel, angle, mid_x)
    if not available:
        raise PlanningError("parcel has no road edge (role 'front')")
    use = ends or available
    if any(e not in available for e in use):
        raise PlanningError(f"requested ends {use} not in road ends {available}")
    parcel_area = parcel.area_tapu_m2 or parcel.area_computed_m2
    cap = params.taks * parcel_area

    def local_angle(a: float, r: tuple[float, float, float, float]) -> float:
        """Direction of the party edges next to the block (x-range +-3 m), else the global one."""
        sx = sy = 0.0
        for e in parcel.edges:
            if e.role != EdgeRole.SIDE_PARTY:
                continue
            mx = to_axis(((e.a[0] + e.b[0]) / 2, (e.a[1] + e.b[1]) / 2), a)[0]
            if r[0] - 3.0 <= mx <= r[1] + 3.0:
                dx, dy = e.b[0] - e.a[0], e.b[1] - e.a[1]
                if dx < -1e-9 or (abs(dx) <= 1e-9 and dy < 0):
                    dx, dy = -dx, -dy
                sx, sy = sx + dx, sy + dy
        return math.atan2(sy, sx) if (sx or sy) else a

    def fit_end(end: str, depth: float) -> tuple[float, tuple[float, float, float, float]] | None:
        ang = angle
        result = None
        for _ in range(3):
            r = fit_block(to_ax_poly(ang), end, depth)
            if r is None:
                return result
            result = (ang, r)
            new_ang = local_angle(ang, r)
            if abs(new_ang - ang) < 1e-4:
                break
            ang = new_ang
        return result

    depth = 13.0
    fits: dict[str, tuple[float, tuple[float, float, float, float]]] = {}
    for _ in range(5):
        fits = {}
        for end in use:
            f = fit_end(end, depth)
            if f is None:
                raise PlanningError(f"no {depth:.2f} m deep block fits at the {end} end")
            fits[end] = f
        total_w = sum(f[1][3] - f[1][2] for f in fits.values())
        new = min(MAX_BLOCK_D, _floor_mod(cap / total_w))
        if new < MIN_BLOCK_D:
            raise PlanningError(f"TAKS leaves only {new:.2f} m block depth for {len(use)} block(s)")
        if abs(new - depth) < 1e-9:
            break
        depth = new

    party_lines = [LineString([e.a, e.b]) for e in parcel.edges if e.role == EdgeRole.SIDE_PARTY]
    names = {0: "Zemin Kat"}
    levels = [Level(id=f"L{k}", name=names.get(k, f"{k}. Kat"), elevation=round(k * floor_height, 4),
                    height=floor_height) for k in range(floors)]
    levels.append(Level(id="R", name="Çatı", elevation=round(floors * floor_height, 4), height=PARAPET))

    walls: list[Wall] = []
    rooms: list[Room] = []
    openings: list[Opening] = []
    slabs: list[Slab] = []
    stairs: list[Stair] = []
    roofs: list[Roof] = []
    footprints: list[list[Pt]] = []
    infos: list[BlockInfo] = []
    risers, riser_h, tread, _zone = stair_numbers(floor_height)

    for bi, end in enumerate(use, start=1):
        b_angle, (x0, x1, ylo, yhi) = fits[end]
        width, d = yhi - ylo, x1 - x0
        blk = f"B{bi}"
        if end == "min":
            org, ev_ax, eu_ax = (x0, yhi), (1.0, 0.0), (0.0, -1.0)
        else:
            org, ev_ax, eu_ax = (x1, ylo), (-1.0, 0.0), (0.0, 1.0)
        o_w = from_axis(org, b_angle)
        ev = from_axis(ev_ax, b_angle)
        eu = from_axis(eu_ax, b_angle)

        def w_pt(u: float, v: float, o_w=o_w, eu=eu, ev=ev) -> Pt:
            return _r((o_w[0] + eu[0] * u + ev[0] * v, o_w[1] + eu[1] * u + ev[1] * v))

        corners = [w_pt(0, 0), w_pt(width, 0), w_pt(width, d), w_pt(0, d)]
        footprints.append(_ccw(corners))

        def side_gap(u: float, w_pt=w_pt, d=d) -> float:
            pts = [Point(w_pt(u, v)) for v in (0.0, d)]
            return max(min((pl.distance(p) for pl in party_lines), default=math.inf) for p in pts)

        gl, gr = side_gap(0.0), side_gap(width)
        left_party, right_party = gl <= PARTY_TOL, gr <= PARTY_TOL
        infos.append(BlockInfo(id=blk, road_end=end, width=round(width, 4), depth=round(d, 4),
                               party_left=left_party, party_right=right_party,
                               gap_left_m=round(gl, 3), gap_right_m=round(gr, 3)))
        tiles, geo = block_tiles(width, d, floor_height)
        int_walls = interior_walls(tiles)
        tile_by_key = {t.key: t for t in tiles}
        ua, ub, v_s, zone = geo["ua"], geo["ub"], geo["vS"], geo["zone"]

        for k in range(floors):
            L = f"L{k}"
            pre = f"{L}-{blk}"

            def add_wall(name, a, b, typ, thick, facade=None, pre=pre, L=L):
                walls.append(Wall(id=f"W-{pre}-{name}", level=L, a=w_pt(*a), b=w_pt(*b), type=typ,
                                  thickness=thick, height=floor_height, facade=facade))

            add_wall("FRONT", (TE / 2, TE / 2), (width - TE / 2, TE / 2), "ext_brick", TE, "front")
            add_wall("REAR", (width - TE / 2, d - TE / 2), (TE / 2, d - TE / 2), "ext_brick", TE, "rear")
            add_wall("PARTY-L", (TE / 2, TE / 2), (TE / 2, d - TE / 2),
                     "party" if left_party else "ext_brick", TE, None if left_party else "side")
            add_wall("PARTY-R", (width - TE / 2, TE / 2), (width - TE / 2, d - TE / 2),
                     "party" if right_party else "ext_brick", TE, None if right_party else "side")
            ids: list[str] = []
            seen: dict[tuple[str, str], int] = {}
            for s in int_walls:
                idx = seen.get(s.pair, 0)
                seen[s.pair] = idx + 1
                name = f"{s.pair[0]}~{s.pair[1]}" + (f"-{idx + 1}" if idx else "")
                add_wall(name, s.a, s.b, s.type, s.thickness)
                ids.append(f"W-{pre}-{name}")

            for t in tiles:
                poly = unary_union([box(r[0], r[2], r[1], r[3]) for r in t.rects]).simplify(1e-9)
                ring = _ccw([w_pt(*c) for c in list(poly.exterior.coords)[:-1]])
                unit = f"U-{pre}-{t.unit}" if t.unit else None
                rooms.append(Room(id=f"R-{pre}-{t.key}", name=t.name, type=t.type, level=L, unit=unit,
                                  outline=ring, ventilation=t.vent))

            def wall_for(a: str, b: str, vertical: bool | None = None, ids=ids):
                pair = tuple(sorted((a, b)))
                cand = [i for i, s in enumerate(int_walls) if s.pair == pair and
                        (vertical is None or math.isclose(s.a[0], s.b[0]) == vertical)]
                if not cand:
                    raise PlanningError(f"no wall between {a} and {b}")
                i = max(cand, key=lambda i: math.dist(int_walls[i].a, int_walls[i].b))
                return int_walls[i], ids[i]

            def door(name, a, b, width_m, role, vertical=None, h=2.1, L=L):
                s, wid = wall_for(a, b, vertical)
                mid = ((s.a[0] + s.b[0]) / 2, (s.a[1] + s.b[1]) / 2)
                length = math.dist(s.a, s.b)
                if length < width_m + 0.2:
                    raise PlanningError(f"wall {a}~{b} too short ({length:.2f} m) for a door")
                openings.append(Opening(id=f"O-{pre}-{name}", kind="door", role=role, level=L,
                                        host_wall=wid, at=w_pt(*mid), width=width_m, height=h,
                                        family_hint="door"))

            def window(name, host, at, width_m, L=L, h=1.4, sill=0.9):
                openings.append(Opening(id=f"O-{pre}-{name}", kind="window", role="window", level=L,
                                        host_wall=f"W-{pre}-{host}", at=w_pt(*at), width=width_m,
                                        height=h, sill=sill, family_hint="window"))

            if k == 0:
                openings.append(Opening(id=f"O-{pre}-MAIN", kind="door", role="main_entry", level=L,
                                        host_wall=f"W-{pre}-FRONT", at=w_pt(width / 2, TE / 2),
                                        width=1.2, height=2.2, family_hint="door"))
                openings.append(Opening(id=f"O-{pre}-REAR-EXIT", kind="door", role="rear_exit", level=L,
                                        host_wall=f"W-{pre}-REAR", at=w_pt(width / 2, d - TE / 2),
                                        width=1.0, height=2.1, family_hint="door"))
            else:
                window("STAIR-FRONT", "FRONT", (width / 2, TE / 2), 1.2)
                window("STAIR-REAR", "REAR", (width / 2, d - TE / 2), 1.2)
            for s in ("A", "B"):
                door(f"{s}-ENTRY", f"{s}-HOL", "CORE-LOBBY", 0.9, "flat_entry")
                door(f"{s}-SALON", f"{s}-SALON", f"{s}-HOL", 0.9, "interior", vertical=False)
                door(f"{s}-BED1", f"{s}-BED1", f"{s}-HOL", 0.9, "interior", vertical=False)
                for key, wd in (("BANYO", 0.8), ("WC", 0.8), ("MUTFAK", 0.9), ("BED2", 0.9)):
                    door(f"{s}-{key}", f"{s}-{key}", f"{s}-HOL", wd, "interior", vertical=True)
                for t in (tile_by_key[f"{s}-SALON"], tile_by_key[f"{s}-BED1"]):
                    u0, u1, v0, v1 = t.rects[0]
                    n = 2 if (u1 - u0) >= 4.0 else 1
                    for i in range(n):
                        window(f"{t.key}-{i + 1}", "FRONT", (u0 + (u1 - u0) * (i + 0.5) / n, TE / 2),
                               1.5 if (u1 - u0) >= 3.2 else 1.2)
                for t, wd in ((tile_by_key[f"{s}-BED2"], 1.5), (tile_by_key[f"{s}-MUTFAK"], 1.0)):
                    u0, u1, _, _ = t.rects[0]
                    window(f"{t.key}-1", "REAR", ((u0 + u1) / 2, d - TE / 2), wd)

            opening = None
            if k >= 1:
                opening = _ccw([w_pt(ua, v_s + tread), w_pt(ub, v_s + tread),
                                w_pt(ub, v_s + zone), w_pt(ua, v_s + zone)])
            slabs.append(Slab(id=f"S-{pre}", level=L, outline=_ccw(corners),
                              openings=[opening] if opening else [], thickness=SLAB_T))
        for k in range(floors - 1):
            stairs.append(Stair(
                id=f"ST-{blk}-L{k}-L{k + 1}", from_level=f"L{k}", to_level=f"L{k + 1}", run_width=RUN_W,
                well_width=WELL, risers=risers, riser_h=riser_h, tread_d=tread, landing_depth=LANDING,
                origin=w_pt(ua, v_s), direction=_r(ev), side=_r(eu), zone_length=zone))
        roofs.append(Roof(id=f"ROOF-{blk}", outline=_ccw(corners), parapet_h=PARAPET, thickness=SLAB_T))

    fp_area = round(sum(Polygon(f).area for f in footprints), 4)
    block_gap = None
    if len(footprints) == 2:
        block_gap = round(Polygon(footprints[0]).distance(Polygon(footprints[1])), 4)
    party_gap = max((g for i in infos for g, p in ((i.gap_left_m, i.party_left),
                                                   (i.gap_right_m, i.party_right)) if p), default=0.0)
    loose = [f"{i.id} {'sol' if not i.party_left else 'sağ'} yüz {max(i.gap_left_m, i.gap_right_m):.2f} m"
             for i in infos if not (i.party_left and i.party_right)]
    spec = BuildingSpec(
        project=Project(name=f"{parcel.parcel_id} - {floors} katli bitisik nizam",
                        parcel_id=parcel.parcel_id),
        levels=levels, blocks=infos, footprints=footprints, walls=walls, slabs=slabs, stairs=stairs,
        rooms=rooms, openings=openings, roofs=roofs,
        derived=Derived(footprint_area_m2=fp_area, gross_area_m2=round(fp_area * floors, 4),
                        taks=round(fp_area / parcel_area, 4),
                        kaks=round(fp_area * floors / parcel_area, 4), blocks=len(infos),
                        block_gap_m=block_gap, party_gap_max_m=round(party_gap, 3)),
        known_gaps=[
            "Merdiven çatıya ulaşmıyor (PAİY Madde 31(1)(b)).",
            "Yangın kaçış genişliği hesabı yapılmadı (Madde 31(1)(a) ön şartı 1.20 m sağlanıyor).",
            "Pencere/aydınlatma alan oranı kontrol edilmedi.",
            "Duvar tipleri ve kapı/pencere aileleri Revit tarafında varsayılan.",
            "Bitişik duvar, parsel sınırına en fazla `party_gap_max_m` kadar uzakta; TKGM koordinat "
            "hassasiyeti ≈ 1 m olduğundan kesin oturtma aplikasyon krokisiyle yapılır.",
        ] + ([f"Komşu sınırından {PARTY_TOL} m'den uzak kalan yan yüz(ler): {', '.join(loose)}; "
              "bu yüz bitişik sayılmadı (cephe duvarı)."] if loose else []),
    )
    return spec.model_copy(update={"spec_id": _hash_spec(spec)})
