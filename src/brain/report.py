"""Standalone HTML report: parcel + setback SVG, check table with citations."""

from __future__ import annotations

from html import escape

from jinja2 import Environment, select_autoescape

from .schemas import EdgeRole, ParcelSpec, ZoningParams, ZoningReport

ROLE_COLOR = {
    EdgeRole.FRONT: "#c0392b",
    EdgeRole.REAR: "#2471a3",
    EdgeRole.SIDE_FREE: "#d68910",
    EdgeRole.SIDE_PARTY: "#707b7c",
    EdgeRole.UNKNOWN: "#000000",
}
STATUS_LABEL = {"pass": "UYGUN", "fail": "UYGUNSUZ", "warn": "UYARI", "assumed": "VARSAYIM"}

TEMPLATE = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>İmar Uygunluk Raporu · {{ parcel.parcel_id }}</title>
<style>
body{font:15px/1.5 system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#1b2631}
h1{font-size:1.4rem;margin-bottom:.2rem}.sub{color:#566573}
.banner{background:#fdebd0;border:2px solid #d68910;padding:.6rem 1rem;border-radius:6px;margin:1rem 0;font-weight:600}
table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{border:1px solid #d5d8dc;padding:.4rem .6rem;text-align:left;vertical-align:top}
th{background:#f4f6f7}.s-pass{color:#1e8449;font-weight:700}.s-fail{color:#c0392b;font-weight:700}
.s-warn,.s-assumed{color:#b9770e;font-weight:700}.verified{color:#1e8449}.unverified{color:#b9770e}
.legend span{display:inline-block;margin-right:1rem}.sw{display:inline-block;width:.8rem;height:.8rem;margin-right:.3rem}
svg{background:#fbfcfc;border:1px solid #d5d8dc;width:100%;max-height:520px}
</style></head><body>
<h1>İmar Uygunluk Raporu</h1>
<div class="sub">{{ parcel.parcel_id }}{% if admin %} · {{ admin }}{% endif %} · kaynak: {{ parcel.source.type }}</div>
{% if report.demo_assumption %}<div class="banner">DEMO VARSAYIMI — imar parametreleri gerçek bir imar durumu belgesinden alınmamıştır.</div>{% endif %}
<p>Parsel alanı: <b>{{ "%.2f"|format(area) }} m²</b> · Yapılaşma alanı: <b>{{ "%.2f"|format(report.buildable_area_m2) }} m²</b>
· Nizam: <b>{{ params.nizam }}</b> · TAKS {{ params.taks }} · KAKS {{ params.kaks }}
{% if params.hmax_m %}· Hmax {{ params.hmax_m }} m{% endif %}</p>
{{ svg|safe }}
<div class="legend">{% for label,color in legend %}<span><i class="sw" style="background:{{ color }}"></i>{{ label }}</span>{% endfor %}
<span><i class="sw" style="background:#a9dfbf"></i>yapılaşma alanı</span>
<span><i class="sw" style="background:#f1948a"></i>bina blokları</span></div>
<h2>Kontroller</h2>
<table><tr><th>Kural</th><th>Durum</th><th>Gerçek</th><th>Sınır</th><th>Açıklama / Atıf</th></tr>
{% for c in report.checks %}<tr><td>{{ c.id }}</td><td class="s-{{ c.status }}">{{ labels[c.status] }}</td>
<td>{{ c.actual if c.actual is not none else "" }}</td><td>{{ c.limit if c.limit is not none else "" }}</td>
<td>{{ c.message }}{% if c.citation %}<br><small class="{{ 'verified' if c.citation.verified else 'unverified' }}">{{ c.citation.ref }} · {{ "doğrulandı" if c.citation.verified else "doğrulanmadı" }}</small>{% else %}<br><small class="unverified">atıf yok</small>{% endif %}</td></tr>{% endfor %}
</table>
<p><b>Sonuç: <span class="s-{{ report.verdict }}">{{ "UYGUN" if report.verdict == "pass" else "UYGUNSUZ" }}</span></b>
({{ counts }})</p>
<p class="sub">"VARSAYIM": değer, parselin imar durumu belgesinden doğrulanmadı. "UYARI": PAİY varsayılanının altında; yalnız plan notları izin veriyorsa geçerli.</p>
</body></html>"""


def _svg(parcel: ParcelSpec, report: ZoningReport, footprints: list | None = None) -> str:
    xs = [p[0] for p in parcel.ring_local]
    ys = [p[1] for p in parcel.ring_local]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    pad = max(maxx - minx, maxy - miny) * 0.08
    w, h = maxx - minx + 2 * pad, maxy - miny + 2 * pad

    def pt(p: tuple[float, float]) -> str:
        return f"{p[0] - minx + pad:.3f},{maxy - p[1] + pad:.3f}"  # flip y

    parts = [f'<svg viewBox="0 0 {w:.2f} {h:.2f}" xmlns="http://www.w3.org/2000/svg">',
             f'<polygon points="{" ".join(pt(p) for p in parcel.ring_local)}" fill="#eaf2f8" '
             f'stroke="none"/>']
    if report.buildable_polygon:
        parts.append(f'<polygon points="{" ".join(pt(p) for p in report.buildable_polygon)}" '
                     f'fill="#a9dfbf" stroke="#1e8449" stroke-width="{w / 400:.3f}"/>')
    for f in footprints or []:
        parts.append(f'<polygon points="{" ".join(pt(p) for p in f)}" fill="#f1948a" '
                     f'stroke="#922b21" stroke-width="{w / 300:.3f}"/>')
    fs = w / 40
    for e in parcel.edges:
        parts.append(f'<line x1="{pt(e.a).split(",")[0]}" y1="{pt(e.a).split(",")[1]}" '
                     f'x2="{pt(e.b).split(",")[0]}" y2="{pt(e.b).split(",")[1]}" '
                     f'stroke="{ROLE_COLOR[e.role]}" stroke-width="{w / 150:.3f}"/>')
        mx, my = (e.a[0] + e.b[0]) / 2, (e.a[1] + e.b[1]) / 2
        parts.append(f'<text x="{pt((mx, my)).split(",")[0]}" y="{pt((mx, my)).split(",")[1]}" '
                     f'font-size="{fs:.2f}" text-anchor="middle" fill="#1b2631">'
                     f'{e.i}: {e.length:.1f} m</text>')
    parts.append("</svg>")
    return "".join(parts)


def render_report(parcel: ParcelSpec, report: ZoningReport, params: ZoningParams,
                  footprints: list | None = None) -> str:
    env = Environment(autoescape=select_autoescape(["html"]))
    admin = ""
    if parcel.admin:
        a = parcel.admin
        admin = f"{a.il} / {a.ilce} / {a.mahalle} · ada {a.ada} parsel {a.parsel}"
    counts = ", ".join(
        f"{STATUS_LABEL[s]} {sum(c.status == s for c in report.checks)}"
        for s in ("pass", "assumed", "warn", "fail") if any(c.status == s for c in report.checks))
    return env.from_string(TEMPLATE).render(
        parcel=parcel, report=report, params=params, admin=escape(admin),
        area=parcel.area_tapu_m2 or parcel.area_computed_m2, svg=_svg(parcel, report, footprints),
        labels=STATUS_LABEL, counts=counts,
        legend=[("ön", ROLE_COLOR[EdgeRole.FRONT]), ("arka", ROLE_COLOR[EdgeRole.REAR]),
                ("yan (serbest)", ROLE_COLOR[EdgeRole.SIDE_FREE]),
                ("yan (bitişik)", ROLE_COLOR[EdgeRole.SIDE_PARTY])])
