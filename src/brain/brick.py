"""Klinker brick layout for `create_brick_panel` ops (pure geometry, no Revit).

A panel covers the outer face of one exterior wall. Bricks lie in courses of pitch (height + joint); each
course is a list of [u0, u1] spans along the wall (u = metres from the wall's `a` end). Bond, opening cuts and
end cuts are decided here, once; the Revit add-in only turns each span into a box. The relief (how far a brick
stands proud of the wall face) is added by the add-in.

LODs: `full` one brick per span; `courses` one strip per course (joints only horizontal).
"""

from __future__ import annotations

import math
from typing import Any

from .schemas import Op

MIN_CUT_M = 0.05          # brick pieces shorter than this are dropped
LODS = ("full", "courses")


def _spans(u_start: float, u_end: float, brick: dict[str, float], bond: str, course: int) -> list[tuple[float, float]]:
    """Brick spans of one course over [u_start, u_end], ignoring openings."""
    s, h, j = brick["length"], brick["depth"], brick["joint"]
    if bond == "flemish":
        unit = [s, h]
        pitch = s + h + 2 * j
        shift = (pitch / 2) if course % 2 else 0.0
    else:
        unit = [s]
        pitch = s + j
        shift = (pitch / 2) if course % 2 else 0.0
    out: list[tuple[float, float]] = []
    u = u_start - shift
    k = 0
    while u < u_end - 1e-9:
        length = unit[k % len(unit)]
        out.append((u, u + length))
        u += length + j
        k += 1
    return [(max(a, u_start), min(b, u_end)) for a, b in out if min(b, u_end) - max(a, u_start) >= MIN_CUT_M]


def _cut(spans: list[tuple[float, float]], holes: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out = spans
    for h0, h1 in holes:
        nxt: list[tuple[float, float]] = []
        for a, b in out:
            if b <= h0 or a >= h1:
                nxt.append((a, b))
                continue
            if h0 - a >= MIN_CUT_M:
                nxt.append((a, h0))
            if b - h1 >= MIN_CUT_M:
                nxt.append((h1, b))
        out = nxt
    return out


def layout(args: dict[str, Any]) -> dict[str, Any]:
    """Courses and statistics for one `create_brick_panel` op's args."""
    ax, ay = args["a"]
    bx, by = args["b"]
    length = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / length, (by - ay) / length
    ext = args["thickness"] / 2                      # outer face runs corner to corner
    u0, u1 = -ext, length + ext
    brick = args["brick"]
    pitch_z = brick["height"] + brick["joint"]
    n_courses = int((args["height"] + brick["joint"]) / pitch_z + 1e-9)

    holes: list[tuple[float, float, float, float]] = []
    for o in args.get("openings", []):
        ox, oy = o["at"]
        u = (ox - ax) * ux + (oy - ay) * uy
        holes.append((u - o["width"] / 2, u + o["width"] / 2, o["sill"], o["sill"] + o["height"]))

    lod = args.get("lod", "full")
    courses: list[dict[str, Any]] = []
    count = 0
    area = 0.0
    for c in range(n_courses):
        z0 = c * pitch_z
        z1 = z0 + brick["height"]
        h = [(a, b) for a, b, lo, hi in holes if lo < z1 and hi > z0]
        if lod == "courses":
            spans = _cut([(u0, u1)], h)
        else:
            spans = _cut(_spans(u0, u1, brick, args.get("bond", "stretcher"), c), h)
        if not spans:
            continue
        courses.append({"z": round(z0, 4), "u": [[round(a, 4), round(b, 4)] for a, b in spans]})
        count += len(spans)
        area += sum(b - a for a, b in spans) * brick["height"]
    return {"courses": courses, "pieces": count, "face_area_m2": round(area, 4), "lod": lod}


def net_wall_area(args: dict[str, Any]) -> float:
    """Outer-face area of the panel minus openings (the area bricks and joints share)."""
    ax, ay = args["a"]
    bx, by = args["b"]
    length = math.hypot(bx - ax, by - ay) + args["thickness"]
    return length * args["height"] - sum(o["width"] * o["height"] for o in args.get("openings", []))


def with_layout(ops: list[Op], lod: str = "full") -> list[Op]:
    """Copies of `ops` where every create_brick_panel carries its computed layout (sent to the add-in)."""
    if lod not in LODS:
        raise ValueError(f"lod must be one of {LODS}")
    out: list[Op] = []
    for o in ops:
        if o.op == "create_brick_panel":
            args = {**o.args, "lod": lod}
            args["layout"] = layout(args)
            o = o.model_copy(update={"args": args})
        out.append(o)
    return out


def stats(ops: list[Op], lod: str = "full") -> dict[str, Any]:
    panels = [layout({**o.args, "lod": lod}) for o in ops if o.op == "create_brick_panel"]
    return {"panels": len(panels), "pieces": sum(p["pieces"] for p in panels),
            "face_area_m2": round(sum(p["face_area_m2"] for p in panels), 2), "lod": lod}


def expected_pieces(ops: list[Op], lod: str = "full") -> dict[str, int]:
    """Pieces each panel must have in the model, by spec ref (what verify_model compares with)."""
    return {o.spec_ref: layout({**o.args, "lod": lod})["pieces"] for o in ops if o.op == "create_brick_panel"}
