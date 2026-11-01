"""Write out/parcel_<id>.html: parcel outline with numbered edges (to choose edge roles).

usage: uv run python tools/parcel_view.py data/parcels/karatay-buyuksinan-1495-26.geojson
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from brain.parcel import parcel_from_geojson
from brain.schemas import ParcelSource

path = Path(sys.argv[1])
feature = json.loads(path.read_text(encoding="utf-8"))
tapu = float(feature["properties"]["alan"].replace(".", "").replace(",", "."))
p = parcel_from_geojson(feature, path.stem, source=ParcelSource(type="tkgm"), area_tapu_m2=tapu)

xs = [q[0] for q in p.ring_local]
ys = [q[1] for q in p.ring_local]
pad = 6.0
minx, maxy = min(xs) - pad, max(ys) + pad
w, h = max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad


def pt(q):
    return f"{q[0] - minx:.2f},{maxy - q[1]:.2f}"


svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.1f} {h:.1f}" '
       f'style="width:100%;height:92vh" font-family="sans-serif">',
       f'<polygon points="{" ".join(pt(q) for q in p.ring_local)}" fill="#eaf2f8" '
       f'stroke="#1b4f72" stroke-width="0.4"/>']
for e in p.edges:
    mx, my = (e.a[0] + e.b[0]) / 2, (e.a[1] + e.b[1]) / 2
    x, y = pt((mx, my)).split(",")
    svg.append(f'<text x="{x}" y="{y}" font-size="2.2" fill="#c0392b" font-weight="bold" '
               f'text-anchor="middle">{e.i} ({e.length:.1f} m)</text>')
for i, q in enumerate(p.ring_local):
    x, y = pt(q).split(",")
    svg.append(f'<circle cx="{x}" cy="{y}" r="0.5" fill="#1b4f72"/>')
svg.append(f'<text x="2" y="4" font-size="2.4">Kuzey ↑ · {path.stem} · tapu {tapu:.2f} m² · '
           f'hesap {p.area_computed_m2:.2f} m²</text></svg>')
out = ROOT / "out" / f"parcel_{path.stem}.html"
out.write_text(f'<body style="margin:0;background:#fff">{"".join(svg)}</body>', encoding="utf-8")
print(out)
