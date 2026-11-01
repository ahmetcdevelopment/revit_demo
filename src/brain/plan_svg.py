"""Floor-plan SVG of one level (rooms, walls, openings) for reports and visual checks."""

from __future__ import annotations

import math

from shapely.geometry import LineString

from .schemas import BuildingSpec

ROOM_FILL = {"living": "#fdebd0", "bedroom": "#d6eaf8", "bath": "#d1f2eb", "wc": "#d1f2eb",
             "hall": "#f2f3f4", "kitchen": "#fcf3cf", "stair": "#e8daef", "core_hall": "#eaecee"}


def plan_svg(spec: BuildingSpec, level: str = "L1") -> str:
    xs = [p[0] for f in spec.footprints for p in f]
    ys = [p[1] for f in spec.footprints for p in f]
    pad = 1.0
    minx, maxy = min(xs) - pad, max(ys) + pad
    w, h = max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad

    def pt(p):
        return f"{p[0] - minx:.3f},{maxy - p[1]:.3f}"

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.2f} {h:.2f}" '
           f'font-family="sans-serif">']
    for r in (r for r in spec.rooms if r.level == level):
        out.append(f'<polygon points="{" ".join(pt(p) for p in r.outline)}" '
                   f'fill="{ROOM_FILL.get(r.type, "#fff")}" stroke="none"/>')
        cx = sum(p[0] for p in r.outline) / len(r.outline)
        cy = sum(p[1] for p in r.outline) / len(r.outline)
        x, y = pt((cx, cy)).split(",")
        out.append(f'<text x="{x}" y="{y}" font-size="0.32" text-anchor="middle">{r.name}</text>')
    for wl in (x for x in spec.walls if x.level == level):
        (ax, ay), (bx, by) = pt(wl.a).split(","), pt(wl.b).split(",")
        out.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="#212f3d" '
                   f'stroke-width="{wl.thickness:.3f}"/>')
    for o in (x for x in spec.openings if x.level == level):
        wall = next(x for x in spec.walls if x.id == o.host_wall)
        dx, dy = wall.b[0] - wall.a[0], wall.b[1] - wall.a[1]
        n = math.hypot(dx, dy)
        ux, uy = dx / n, dy / n
        a = (o.at[0] - ux * o.width / 2, o.at[1] - uy * o.width / 2)
        b = (o.at[0] + ux * o.width / 2, o.at[1] + uy * o.width / 2)
        col = "#c0392b" if o.kind == "door" else "#2e86c1"
        (x1, y1), (x2, y2) = pt(a).split(","), pt(b).split(",")
        out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" '
                   f'stroke-width="{wall.thickness * 0.6:.3f}"/>')
    for s in spec.slabs:
        if s.level == level:
            for hole in s.openings:
                out.append(f'<polygon points="{" ".join(pt(p) for p in hole)}" fill="none" '
                           f'stroke="#7d3c98" stroke-dasharray="0.2 0.1" stroke-width="0.05"/>')
    out.append("</svg>")
    return "".join(out)


def level_bounds(spec: BuildingSpec) -> tuple[float, float]:
    pts = [p for f in spec.footprints for p in f]
    ln = LineString(pts)
    return ln.bounds[2] - ln.bounds[0], ln.bounds[3] - ln.bounds[1]
