"""The final report: one self-contained HTML file (images embedded) for the architecture firm.

Sections: summary, parcel and zoning, plan, the Revit model (screenshots), spec <-> Revit <-> IFC table,
verification, IFC/IDS, scenario results, limits. Everything that was not measured says so.
"""

from __future__ import annotations

import base64
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from shapely.geometry import Polygon

from .plan_svg import plan_svg
from .report import STATUS_LABEL, _svg
from .schemas import BuildingSpec, ParcelSpec, ZoningParams, ZoningReport

CSS = """
:root{--ink:#1b2631;--mute:#566573;--line:#d5d8dc;--ok:#1e8449;--bad:#c0392b;--warn:#b9770e;--bg:#fff}
@media (prefers-color-scheme:dark){:root{--ink:#e8eaed;--mute:#aab2bd;--line:#3a4048;--bg:#14181c}}
body{font:15px/1.55 system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:var(--ink);background:var(--bg)}
h1{font-size:1.6rem;margin:.2rem 0}h2{margin-top:2.2rem;border-bottom:2px solid var(--line);padding-bottom:.3rem;font-size:1.2rem}
.sub{color:var(--mute)}.banner{background:#fdebd0;color:#4a3000;border:2px solid #d68910;padding:.6rem 1rem;border-radius:6px;margin:1rem 0;font-weight:600}
table{border-collapse:collapse;width:100%;margin:.8rem 0;font-size:.93rem}th,td{border:1px solid var(--line);padding:.35rem .55rem;text-align:left;vertical-align:top}
th{background:rgba(127,127,127,.12)}td.n{text-align:right;font-variant-numeric:tabular-nums}
.ok{color:var(--ok);font-weight:700}.bad{color:var(--bad);font-weight:700}.warn{color:var(--warn);font-weight:700}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem}
figure{margin:0}figcaption{font-size:.85rem;color:var(--mute);margin-top:.2rem}
img,svg{max-width:100%;height:auto;border:1px solid var(--line);border-radius:4px}svg{background:#fbfcfc;width:100%}
.kpi{display:flex;flex-wrap:wrap;gap:.8rem;margin:1rem 0}.kpi div{border:1px solid var(--line);border-radius:6px;padding:.5rem .9rem}
.kpi b{display:block;font-size:1.3rem}.kpi span{color:var(--mute);font-size:.82rem}
small{color:var(--mute)}pre{white-space:pre-wrap;font-size:.85rem}
"""


def _img(path: Path, alt: str) -> str:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f'<img alt="{escape(alt)}" src="data:image/png;base64,{data}">'


def _mark(ok: bool | None) -> str:
    return "<span class='ok'>✔</span>" if ok else ("<span class='bad'>✘</span>" if ok is not None else "—")


def three_way(spec: BuildingSpec, model: dict[str, Any] | None, ifc: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Rows of (item, spec, revit, ifc). `None` means "not measured", never "zero"."""
    doors = sum(o.kind == "door" for o in spec.openings)
    room_area = round(sum(Polygon(r.outline).area for r in spec.rooms), 2)
    counts = model["counts"] if model else None
    rooms_model = round(sum(r["area_m2"] for r in model["rooms"]), 2) if model else None
    summ = ifc["summary"] if ifc else None
    klinker_model = None
    if model:
        import re
        klinker_model = sum(int(m.group(1)) for p in model.get("brick_panels", [])
                            if (m := re.search(r"pieces=(\d+)", p.get("comments") or "")))
    rows = [
        ("Kat (level / IfcBuildingStorey)", len(spec.levels), counts and counts["levels"], summ and summ["storeys"]),
        ("Duvar", len(spec.walls), counts and counts["walls"], summ and summ["walls"]),
        ("Döşeme", len(spec.slabs), counts and counts["floors"], summ and summ["slabs"]),
        ("Çatı", len(spec.roofs), counts and counts["roofs"], summ and summ["roofs"]),
        ("Mahal (oda)", len(spec.rooms), counts and counts["rooms"], summ and summ["spaces"]),
        ("Mahal alanı toplamı m²", room_area, rooms_model, summ and summ["space_net_area_m2"]),
        ("Kapı", doors, counts and counts["doors"], summ and summ["doors"]),
        ("Pencere", len(spec.openings) - doors, counts and counts["windows"], summ and summ["windows"]),
        ("Merdiven", len(spec.stairs), counts and counts["stairs"], summ and summ["stairs"]),
        ("Klinker panel", sum(1 for w in spec.walls if w.type == "ext_brick" and w.facade), model and len(model.get("brick_panels", [])),
         summ and summ["brick_panels"]),
        ("Klinker tuğla (adet)", None, klinker_model, None),
    ]
    return [{"item": a, "spec": b, "revit": c, "ifc": d} for a, b, c, d in rows]


def _cell(v: Any) -> str:
    return "<td class='n'>—</td>" if v is None else f"<td class='n'>{v}</td>"


def render_project_report(*, parcel: ParcelSpec, params: ZoningParams, zoning: ZoningReport, spec: BuildingSpec,
                          validation: Any, verify_report: dict[str, Any] | None, model: dict[str, Any] | None,
                          ifc: dict[str, Any] | None, ids: dict[str, Any] | None, views_dir: Path | None,
                          scenario_md: str | None, lod: str = "full") -> str:
    d = spec.derived
    area = parcel.area_tapu_m2 or parcel.area_computed_m2
    p: list[str] = [f"<!doctype html><html lang='tr'><head><meta charset='utf-8'>"
                    f"<title>Proje Raporu · {escape(parcel.parcel_id)}</title><style>{CSS}</style></head><body>"]
    p.append(f"<h1>Parselden Revit Modeline · Proje Raporu</h1><div class='sub'>{escape(parcel.parcel_id)} · "
             f"spec {escape(spec.spec_id)} · {datetime.now():%Y-%m-%d %H:%M}</div>")
    if zoning.demo_assumption:
        p.append("<div class='banner'>DEMO VARSAYIMI — imar parametreleri (TAKS, KAKS, kat adedi, çekmeler) bu parselin "
                 "gerçek imar durumu belgesinden alınmamıştır. Parsel geometrisi TKGM'den, komşuluk ve yol bilgisi "
                 "TKGM komşu sorgusundan gelir.</div>")
    kpis = (("parsel m²", f"{area:,.1f}"), ("blok", d.blocks), ("TAKS", d.taks), ("KAKS", d.kaks),
            ("brüt inşaat m²", f"{d.gross_area_m2:,.0f}"), ("duvar", len(spec.walls)), ("mahal", len(spec.rooms)))
    p.append("<div class='kpi'>" + "".join(f"<div><b>{v}</b><span>{k}</span></div>" for k, v in kpis) + "</div>")

    p.append("<h2>1 · Parsel ve imar kontrolü</h2>")
    p.append(_svg(parcel, zoning, spec.footprints))
    p.append("<table><tr><th>Kural</th><th>Durum</th><th>Gerçek</th><th>Sınır</th><th>Açıklama / atıf</th></tr>")
    for c in zoning.checks:
        cls = {"pass": "ok", "fail": "bad"}.get(c.status, "warn")
        cit = (f"<br><small>{escape(c.citation.ref)} · {'doğrulandı' if c.citation.verified else 'doğrulanmadı'}</small>"
               if c.citation else "<br><small>atıf yok</small>")
        p.append(f"<tr><td>{escape(c.id)}</td><td class='{cls}'>{STATUS_LABEL[c.status]}</td>"
                 f"<td class='n'>{'' if c.actual is None else c.actual}</td><td class='n'>{'' if c.limit is None else c.limit}</td>"
                 f"<td>{escape(c.message)}{cit}</td></tr>")
    p.append(f"</table><p><b>Sonuç: <span class='{'ok' if zoning.verdict == 'pass' else 'bad'}'>"
             f"{'UYGUN' if zoning.verdict == 'pass' else 'UYGUNSUZ'}</span></b> · "
             f"<small>VARSAYIM = değer tuttu ama kaynağı doğrulanmadı; UYARI = PAİY varsayılanının altında, plan notuyla aşılabilir.</small></p>")

    p.append("<h2>2 · Plan</h2><div class='grid'>")
    for lv in ("L0", "L1"):
        p.append(f"<figure>{plan_svg(spec, lv)}<figcaption>{'Zemin' if lv == 'L0' else '1. ve 2.'} kat planı (spec'ten çizim)</figcaption></figure>")
    p.append("</div>")
    p.append(f"<p>{d.blocks} blok; blok aralığı {d.block_gap_m} m (PAİY M24(2): toplam ≥ 6 m); komşu parsel yüzlerinde boşluk ≤ "
             f"{d.party_gap_max_m} m. Merdiven: iki kollu, 19 rıht, {spec.stairs[0].riser_h:.4f} m rıht, {spec.stairs[0].tread_d:.2f} m basamak.</p>")

    p.append("<h2>3 · Revit modeli</h2>")
    shots = sorted(views_dir.glob("*.png")) if views_dir and views_dir.exists() else []
    if shots:
        order = sorted(shots, key=lambda f: (0 if "3D" in f.name else 1, f.name))
        p.append("<div class='grid'>")
        for f in order:
            if "Site" in f.name:
                continue
            title = f.stem.split(" - ")[0].replace("_", " ")
            p.append(f"<figure>{_img(f, title)}<figcaption>Revit 2027.3 · {escape(title)}</figcaption></figure>")
        p.append("</div>")
    else:
        p.append("<p><b>Revit görüntüsü yok</b> (Revit bağlı değildi veya dışa aktarılmadı).</p>")
    p.append(f"<p><small>Klinker cephe: tuğla {spec.facade.front.brick.length * 1000:.0f}×{spec.facade.front.brick.height * 1000:.0f} mm, "
             f"derz {spec.facade.front.brick.joint * 1000:.0f} mm, {escape(spec.facade.front.bond)} bağ; LOD <b>{escape(lod)}</b>. "
             f"Tuğlalar duvar yüzünden 2 cm çıkıntılı kaplamadır (tek DirectShape mesh/panel).</small></p>")

    p.append("<h2>4 · Üç yönlü tutarlılık: spec ↔ Revit ↔ IFC</h2>")
    p.append("<table><tr><th>Öğe</th><th>Spec</th><th>Revit modeli</th><th>IFC4</th></tr>")
    for r in three_way(spec, model, ifc):
        p.append(f"<tr><td>{r['item']}</td>{_cell(r['spec'])}{_cell(r['revit'])}{_cell(r['ifc'])}</tr>")
    p.append("</table><p><small>— = ölçülmedi (Revit bağlı değildi veya IFC üretilmedi). IFC'de döşeme sayısı, çatı katmanlarını "
             "da sayar (Revit çatıyı IfcRoof + IfcSlab olarak yazar).</small></p>")

    p.append("<h2>5 · Doğrulama (verify_model)</h2>")
    if verify_report:
        p.append(f"<p>Sonuç: <b class='{'ok' if verify_report['ok'] else 'bad'}'>{'MODEL = SPEC' if verify_report['ok'] else 'FARK VAR'}</b> "
                 f"· Revit uyarısı: {verify_report.get('revit_warnings', 0)}</p><table><tr><th>Kontrol</th><th>Spec</th><th>Model</th><th></th></tr>")
        for r in verify_report["rows"]:
            p.append(f"<tr><td>{escape(r['category'])}</td>{_cell(r['expected'])}{_cell(r['actual'])}<td>{_mark(r['ok'])}</td></tr>")
        p.append("</table>")
        for diff in verify_report["differences"]:
            p.append(f"<p class='bad'>{escape(diff)}</p>")
        if verify_report.get("warning_kinds"):
            p.append("<details><summary>Revit uyarıları (engelleyici değil)</summary><ul>" + "".join(
                f"<li>{k['count']} × {escape(k['text'][:140])}</li>" for k in verify_report["warning_kinds"]) + "</ul></details>")
    else:
        p.append("<p><b>Model doğrulaması çalışmadı</b> (Revit bağlı değildi).</p>")
    if validation is not None:
        p.append(f"<p>Plan doğrulaması (Revit'siz): <b class='{'ok' if validation.ok else 'bad'}'>"
                 f"{'hata yok' if validation.ok else str(len(validation.errors())) + ' hata'}</b>; "
                 f"uyarı: {sum(i.level == 'warn' for i in validation.issues)}.</p>")

    p.append("<h2>6 · IFC4 ve IDS</h2>")
    if ifc and ids:
        p.append(f"<p>Kaynak: <b>{escape(ifc.get('route', ''))}</b> · {ifc['bytes'] / 1e6:.1f} MB · IDS: "
                 f"<b class='{'ok' if ids['ok'] else 'bad'}'>{'tüm şartlar sağlandı' if ids['ok'] else 'eksikler var'}</b> "
                 f"({ids['specifications']} şart)</p>")
        if ids["failed"]:
            p.append("<ul>" + "".join(f"<li class='bad'>{escape(n)}</li>" for n in ids["failed"]) + "</ul>")
        p.append(f"<p><small>Profil: {escape(ids['profile'])}.</small></p>")
    else:
        p.append("<p><b>IFC üretilmedi.</b></p>")
    p.append(REGULATION_NOTE)

    if scenario_md:
        p.append("<h2>7 · Senaryo testleri (gerçek Revit'te)</h2><pre>" + escape(scenario_md) + "</pre>")

    p.append("<h2>8 · Sınırlar</h2><ul>")
    for g in spec.known_gaps:
        p.append(f"<li>{escape(g)}</li>")
    p.append("<li>İmar parametreleri demo varsayımıdır; gerçek imar durumu belgesi gelince tek dosya (<code>data/imar-durumu/demo.yaml</code>) değişir.</li>"
             "<li>TKGM koordinatları ±1 m hassasiyettedir (5 ondalık derece).</li>"
             "<li>Parsel üzerinde bugün iki mevcut bina vardır; model bunları yıkıp yeni bina yapıldığını varsayar, mevcut yapı modellenmedi.</li>"
             "<li>Parapet ve oda etiketleri yok; kapı/pencere şablon ailelerinden (M_Single-Flush, M_Window-Casement-Double).</li>"
             "<li>Revit 2027.3 deneme (ticari olmayan) sürümüdür.</li></ul></body></html>")
    return "".join(p)


REGULATION_NOTE = (
    "<p><small>Yönetmelik atfı: <i>Mimarlık ve Mühendislik Projelerinin Dijital Olarak Hazırlanması Hakkında Yönetmelik</i> "
    "(RG 05.08.2026-33331), yürürlük 1.9.2027. Metinden yalnız Madde 7(2) (mahal numarası), IFC şeması (TS EN ISO 16739-1) ve "
    "SI birim hükümleri okundu; zorunlu IFC sınıf ve öznitelik ekleri (EK-5/EK-6) <b>okunamadı</b>, bu yüzden IDS yönetmeliğe "
    "uygunluk iddia etmez.</small></p>")
