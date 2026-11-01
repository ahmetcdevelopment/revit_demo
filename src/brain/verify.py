"""verify_model: compares a BuildingSpec with what the Revit add-in reads back from the model.

Per-element differences are listed by spec id; the summary rows give the totals a reader can check at
a glance. Walls are measured on their location line: Revit extends a wall end that butts into another
wall to that wall's centre line, so the model may be longer than the spec by up to half a neighbour
thickness per end (WALL_EXTENSION_TOL_M) - the room areas are the real geometric check.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from pydantic import BaseModel, ConfigDict
from shapely.geometry import Polygon

from .schemas import BuildingSpec

WALL_EXTENSION_TOL_M = 0.40
WALL_SHORT_TOL_M = 0.02
THICKNESS_TOL_M = 0.002
AREA_REL_TOL = 0.02          # rooms bounded by walls
# Open core rooms (lobby / stair / rear hall) have no wall between them, only a room separation line whose
# ends Revit snaps to the neighbouring wall faces (measured: ~9 cm shift, 0.25 m2 on a 10 m2 room).
OPEN_ROOM_REL_TOL = 0.05
SLAB_REL_TOL = 0.005
RISER_H_TOL_M = 0.0005
TREAD_TOL_M = 0.002
STAIR_Z_TOL_M = 0.30         # run surfaces may sit a tread-thickness below the level


class Row(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    expected: float | int
    actual: float | int
    ok: bool
    note: str = ""


class VerifyReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    spec_id: str
    rows: list[Row]
    differences: list[str]
    revit_warnings: int = 0
    warning_kinds: list[dict[str, Any]] = []


def _by_ref(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {i["spec_ref"]: i for i in items if i.get("spec_ref")}


def _pieces(comment: str | None) -> int | None:
    m = re.search(r"pieces=(\d+)", comment or "")
    return int(m.group(1)) if m else None


def verify(spec: BuildingSpec, model: dict[str, Any], brick_expected: dict[str, int] | None = None) -> VerifyReport:
    diffs: list[str] = []
    rows: list[Row] = []

    def row(category: str, expected: float, actual: float, ok: bool, note: str = "") -> None:
        rows.append(Row(category=category, expected=round(expected, 3) if isinstance(expected, float) else expected,
                        actual=round(actual, 3) if isinstance(actual, float) else actual, ok=ok, note=note))

    counts = model["counts"]
    row("levels", len(spec.levels), counts["levels"], counts["levels"] == len(spec.levels))

    walls = _by_ref(model["walls"])
    for w in spec.walls:
        m = walls.get(w.id)
        if m is None:
            diffs.append(f"wall {w.id} missing in model")
            continue
        want = math.dist(w.a, w.b)
        if not (-WALL_SHORT_TOL_M <= m["length_m"] - want <= WALL_EXTENSION_TOL_M):
            diffs.append(f"wall {w.id} length {m['length_m']} vs spec {want:.3f}")
        if abs(m["thickness_m"] - w.thickness) > THICKNESS_TOL_M:
            diffs.append(f"wall {w.id} thickness {m['thickness_m']} vs spec {w.thickness}")
    present = sum(1 for w in spec.walls if w.id in walls)
    row("walls", len(spec.walls), present, present == len(spec.walls), "tagged walls found by spec id")
    untagged = len(model["walls"]) - len(walls)
    if untagged:
        diffs.append(f"{untagged} wall(s) in the model are not tagged by the bridge")

    floors = _by_ref(model["floors"])
    slab_area_spec = slab_area_model = 0.0
    for s in spec.slabs:
        want = Polygon(s.outline).area - sum(Polygon(o).area for o in s.openings)
        slab_area_spec += want
        m = floors.get(s.id)
        if m is None:
            diffs.append(f"slab {s.id} missing in model")
            continue
        slab_area_model += m["area_m2"]
        if abs(m["area_m2"] - want) > max(0.05, SLAB_REL_TOL * want):
            diffs.append(f"slab {s.id} area {m['area_m2']} vs spec {want:.3f}")
    row("slab area m2", slab_area_spec, slab_area_model,
        abs(slab_area_model - slab_area_spec) <= SLAB_REL_TOL * max(slab_area_spec, 1))

    rooms = _by_ref(model["rooms"])
    room_area_spec = room_area_model = 0.0
    for r in spec.rooms:
        want = Polygon(r.outline).area
        room_area_spec += want
        m = rooms.get(r.id)
        if m is None:
            diffs.append(f"room {r.id} missing in model")
        elif m["area_m2"] <= 0:
            diffs.append(f"room {r.id} is not enclosed (area 0)")
        else:
            room_area_model += m["area_m2"]
            tol = OPEN_ROOM_REL_TOL if "-CORE-" in r.id else AREA_REL_TOL
            if abs(m["area_m2"] - want) > tol * want:
                diffs.append(f"room {r.id} area {m['area_m2']} vs spec {want:.2f} (> {tol:.0%})")
    row("rooms", len(spec.rooms), sum(1 for r in spec.rooms if r.id in rooms), counts["rooms"] == len(spec.rooms))
    row("room area m2", room_area_spec, room_area_model,
        abs(room_area_model - room_area_spec) <= AREA_REL_TOL * max(room_area_spec, 1))

    stairs = _by_ref(model["stairs"])
    elev = {lv.id: lv.elevation for lv in spec.levels}
    for st in spec.stairs:
        m = stairs.get(st.id)
        if m is None:
            diffs.append(f"stair {st.id} missing in model")
            continue
        if m["risers"] != sum(st.risers):
            diffs.append(f"stair {st.id} risers {m['risers']} vs spec {sum(st.risers)}")
        if abs(m["riser_h_m"] - st.riser_h) > RISER_H_TOL_M:
            diffs.append(f"stair {st.id} riser height {m['riser_h_m']} vs spec {st.riser_h}")
        if abs(m["tread_d_m"] - st.tread_d) > TREAD_TOL_M:
            diffs.append(f"stair {st.id} tread {m['tread_d_m']} vs spec {st.tread_d}")
        if "z_min_m" in m:   # the stair must stand between its two levels, not a storey higher or lower
            lo, hi = elev[st.from_level], elev[st.to_level]
            if m["z_min_m"] < lo - STAIR_Z_TOL_M or m["z_max_m"] > hi + STAIR_Z_TOL_M:
                diffs.append(f"stair {st.id} stands at z {m['z_min_m']}..{m['z_max_m']} m, "
                             f"expected within {lo}..{hi} m")
    row("stairs", len(spec.stairs), counts["stairs"], counts["stairs"] == len(spec.stairs))

    by_cat = Counter(o["category"] for o in model["openings"])
    for kind, cat in (("door", "Doors"), ("window", "Windows")):
        want = sum(1 for o in spec.openings if o.kind == kind)
        row(f"{kind}s", want, by_cat.get(cat, 0), by_cat.get(cat, 0) == want)
    row("roofs", len(spec.roofs), counts.get("roofs", 0), counts.get("roofs", 0) == len(spec.roofs))
    if "room_tags" in counts:
        row("room tags", len(spec.rooms), counts["room_tags"], counts["room_tags"] == len(spec.rooms))

    if brick_expected is not None:
        panels = {p["spec_ref"]: _pieces(p.get("comments")) for p in model.get("brick_panels", [])}
        for ref, want in brick_expected.items():
            got = panels.get(ref)
            if got is None:
                diffs.append(f"klinker panel {ref} missing in model")
            elif got != want:
                diffs.append(f"klinker panel {ref} has {got} pieces vs layout {want}")
        row("klinker panels", len(brick_expected), sum(1 for r in brick_expected if panels.get(r) is not None),
            all(panels.get(r) is not None for r in brick_expected))
        row("klinker pieces", sum(brick_expected.values()), sum(v for v in panels.values() if v),
            all(panels.get(r) == w for r, w in brick_expected.items()))

    for r in rows:
        if not r.ok:
            diffs.append(f"total mismatch: {r.category} spec {r.expected} vs model {r.actual}")
    return VerifyReport(ok=not diffs, spec_id=spec.spec_id, rows=rows, differences=diffs,
                        revit_warnings=model.get("warnings", 0), warning_kinds=model.get("warning_kinds", []))
