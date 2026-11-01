# 02 · Veri Şemaları

Tüm şemalar **Pydantic v2** modeli olarak `src/brain/schemas/` altında tanımlanır, **JSON Schema** olarak `data/schemas/` ya da `out/` içine export edilir. Birimler: **metre**, açı: derece, koordinat: **yerel metrik düzlem** (ENU, orijin = parsel ağırlık merkezi veya ilk köşe; `origin_itrf` saklanır).

## 2.1 ParcelSpec
```jsonc
{
  "schema_version": "1.0",
  "parcel_id": "karatay-sariyakup-20677-13",
  "source": {"type": "tkgm|manual", "retrieved": "2026-10-29", "url": "…", "fixture": "data/parcels/….json"},
  "admin": {"il": "Konya", "ilce": "Karatay", "mahalle": "Sarıyakup", "ada": 20677, "parsel": 13},
  "crs": {"input": "EPSG:4326|EPSG:5254…", "local_origin": [lon, lat], "projected": "EPSG:5254"},
  "ring_local": [[x,y], …],                 // saat yönünün tersi, kapalı değil (son=ilk eklenmez)
  "area_tapu_m2": 0.0,                      // belgedeki alan
  "area_computed_m2": 0.0,                  // shapely hesabı; fark > %1 ise uyarı
  "edges": [
    {"i": 0, "a": [x,y], "b": [x,y], "length": 0.0,
     "role": "front|rear|side_party|side_free|unknown",   // kenar etiketi
     "adjacent": "road|neighbor_parcel|open|unknown",
     "road_name": "Genç Sokak", "road_width_m": null}
  ]
}
```
Kenar etiketleri **insan/Claude girdisidir** (yol cephesi hangisi?) ve `validate_parcel` ile tutarlılığı sınanır (ör. en az 1 `front`).

## 2.2 ZoningParams (imar durumu — gerçek kaynak: imar durumu belgesi)
```jsonc
{
  "schema_version": "1.0",
  "source_doc": {"type": "imar_durumu|demo_assumption", "file": "data/imar-durumu/….pdf", "date": null},
  "nizam": "bitisik|ayrik|blok",
  "taks": 0.0, "kaks": 0.0, "emsal_disi_alan_orani": null,
  "hmax_m": null, "kat_adedi_max": 3,
  "setbacks": {"front": 0.0, "side_free": 0.0, "side_party": 0.0, "rear": 0.0},
  "extras": {"cikma_max_m": null, "siginak": null, "otopark_notu": null},
  "citations": {"setbacks": {"ref": "Plan notu / PAİY md.", "verified": false}}   // alan adı → atıf (kodda dict)
}
```
`source_doc.type = demo_assumption` ise rapor her sayfada **"DEMO VARSAYIMI"** damgası taşır (dürüstlük kuralı).

## 2.3 ZoningReport
```jsonc
{
  "buildable_polygon": [[x,y], …],
  "limits": {"taks_area_m2": 0.0, "kaks_area_m2": 0.0, "hmax_m": 0.0},
  "checks": [
    {"id": "Z-TAKS", "status": "pass|fail|warn|assumed", "actual": 0.0, "limit": 0.0,
     "citation": {"ref": "…", "verified": false}, "message": "…"}
  ],
  "verdict": "pass|fail"
}
```

## 2.4 BuildingSpec (merkezi sözleşme)
```jsonc
{
  "schema_version": "1.0",
  "spec_id": "sha256 kısa özet (içerik adresli)",
  "project": {"name": "…", "parcel_id": "…", "north_angle_deg": 0},
  "levels": [{"id": "L0", "name": "Zemin Kat", "elevation": 0.0, "height": 3.0}],
  "footprint": [[x,y], …],
  "party_walls": [{"edge_i": 1, "thickness": 0.25}],
  "walls": [{"id": "W-L0-001", "level": "L0", "a": [x,y], "b": [x,y], "type": "ext_brick|int_100|party|stair_core", "thickness": 0.0, "facade": "front|rear|side|null"}],
  "slabs": [{"id": "S-L0", "level": "L0", "outline": [[x,y],…], "thickness": 0.2, "openings": [{"id":"O-stair","outline":[…]}]}],
  "roof": {"type": "flat|gable|hip", "outline": [[x,y],…], "slope_deg": 0, "overhang": 0.0},
  "core": {"stair": {"type": "two_run", "width": 1.2, "riser": 0.17, "tread": 0.28, "landing_depth": 1.2, "origin": [x,y], "rotation": 0}},
  "units": [{"id": "U-L1-A", "level": "L1", "rooms": [{"id": "R-…", "name": "Salon", "type": "living|bedroom|kitchen|bath|wc|hall|stair", "outline": [[x,y],…], "min_area": 0.0}], "entrance": {"door": "D-…"}}],
  "openings": [{"id": "D-L1-A-01", "kind": "door|window", "host_wall": "W-…", "offset": 0.0, "width": 0.9, "height": 2.1, "sill": 0.0, "family": "…"}],
  "facade": {"front": {"material": "klinker", "bond": "stretcher|flemish", "brick": {"l": 0.24, "h": 0.052, "d": 0.115, "joint": 0.010}, "color": "#8a3b2a"}},
  "derived": {"gross_area_m2": 0.0, "taks": 0.0, "kaks": 0.0}
}
```
Kurallar: tüm `id`'ler benzersiz ve **kararlı** (aynı girdi → aynı id); referanslar (`level`, `host_wall`) şema sonrası bütünlük kontrolünden geçer; `spec_id` içerikten türetilir (idempotency anahtarı).

## 2.5 Op listesi (derleyici çıktısı)
```jsonc
{"op_id": "0001", "op": "create_level|create_wall|create_floor|create_roof|create_stair|create_room|place_door|place_window|create_brick_panel|set_param",
 "spec_ref": "W-L0-001", "depends_on": ["L0"], "args": {…}}
```
Sıra: Level → Wall → Floor(+açıklık) → Stair → Roof → Room → Door/Window → Brick panel → Param. `depends_on` ile topolojik sıralama; döngü = derleme hatası.

## 2.6 RPC zarfı
```jsonc
{"id": "uuid", "method": "apply_ops|read_back|status|export_ifc", "token": "…", "params": {…}}
→ {"id": "uuid", "ok": true, "result": {…}} | {"ok": false, "error": {"code": "…", "op_id": "…", "message": "…"}}
```

## 2.7 VerifyReport (readback)
`{"expected": n, "found": n, "missing": [spec_id…], "extra": [elementId…], "param_mismatch": […], "warnings": [{"code","count"}], "rooms": [{"spec_id","area_expected","area_actual","ok"}]}`

## 2.8 Şema evrimi
`schema_version` zorunlu; uyumsuz sürüm → `validate_spec` reddeder. Şema değişikliği = `02-karar-kaydi.md`'ye satır.
