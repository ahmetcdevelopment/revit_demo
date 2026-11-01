# 01 · Sistem Mimarisi

## İlke
**LLM niyeti tarif eder, geometriyi deterministik derleyici kurar.** Claude'a düşük seviyeli `create_wall` araçları vermek yerine, Claude yapılandırılmış bir `BuildingSpec` üretir/revize eder; derleyici bunu sıralı, doğrulanabilir `Op` listesine çevirir; ince bir Revit add-in'i op'ları transaction içinde uygular.

## Bileşenler
```
┌─────────────────────────────────────────────────────────────────────┐
│ Claude (Desktop / Code) — mevcut abonelik, API ücreti yok           │
└───────────────┬─────────────────────────────────────────────────────┘
                │ MCP (stdio)
┌───────────────▼─────────────────────────────────────────────────────┐
│ BEYİN  (Python, src/brain)                                          │
│  mcp_server   → araç yüzeyi (aşağıda)                               │
│  parcel       → koordinat, CRS dönüşümü, kenar etiketleme           │
│  zoning       → kural motoru (YAML), yapılaşma alanı, rapor         │
│  planner      → BuildingSpec üretimi (kural tabanlı yerleşim)       │
│  compiler     → Spec → Op listesi (deterministik, sıralı)           │
│  verify       → offline testler + readback karşılaştırma            │
│  ifc          → IfcOpenShell export + IDS doğrulama                 │
│  backends     → RevitBackend (RPC) | IfcBackend (yedek)             │
└───────────────┬─────────────────────────────────────────────────────┘
                │ localhost JSON-RPC (token'lı)
┌───────────────▼─────────────────────────────────────────────────────┐
│ REVIT ADD-IN (C#, src/revit-addin) — ince yürütücü                  │
│  RpcServer → CommandQueue → ExternalEvent handler (ana thread)      │
│  OpExecutors (Level, Wall, Floor, Roof, Stair, Room, Door, Window,  │
│   Brick panel mesh) · TransactionGroup + rollback                   │
│  SpecIdStore (ExtensibleStorage) · Readback · IFC export tetikleme  │
└─────────────────────────────────────────────────────────────────────┘
        çıktılar: out/  (spec.json, ops.json, report.html, model.ifc, readback.json)
```

## MCP araç yüzeyi (az ve anlamlı — LLM'e küçük API)
| Araç | Girdi | Çıktı |
|---|---|---|
| `load_parcel` | il/ilçe/mahalle/ada/parsel **veya** fixture adı | ParcelSpec |
| `load_zoning` | imar durumu dosyası/ID | ZoningParams |
| `check_zoning` | ParcelSpec + ZoningParams | ZoningReport (madde atıflı) |
| `plan_building` | parsel, imar, program | BuildingSpec |
| `validate_spec` | BuildingSpec | offline test sonucu |
| `build_in_revit` | BuildingSpec, mod (`dry_run`/`apply`) | ApplyResult (diff, uyarılar) |
| `verify_model` | spec_id | VerifyReport (readback karşılaştırma) |
| `export_ifc` | spec_id | model.ifc + IDS raporu |
| `get_status` | — | Revit bağlantısı, açık doküman, sürüm |

## Veri akışı (uçtan uca senaryo)
1. `load_parcel` → ParcelSpec (poligon, kenar etiketleri).
2. `load_zoning` + `check_zoning` → yapılaşma poligonu, izin verilen alan/yükseklik.
3. `plan_building` → BuildingSpec; `validate_spec` offline testleri koşar.
4. `build_in_revit(dry_run)` → op listesi + beklenen sayılar; ardından `apply`.
5. `verify_model` → readback ile spec karşılaştırılır; `export_ifc` → IFC + IDS.
6. Rapor (`report.html`) tüm adımların özetini ve madde atıflarını içerir.

## Tasarım desenleri
- **Idempotent reconcile:** Her eleman `spec_id` taşır (ExtensibleStorage). `apply`, spec ile modeli karşılaştırır → ekle/güncelle/sil diff'i uygular; ikinci çalıştırma 0 değişiklik.
- **Atomik uygulama:** Bir `apply` = bir `TransactionGroup`. Hata → rollback; Revit'te tek Undo.
- **Tek yazıcı:** Revit API çağrıları yalnız ana thread'de (`IExternalEventHandler`); RPC thread'i `TaskCompletionSource` ile bekler.
- **Kapalı dünya:** Add-in yalnız bilinen op tiplerini kabul eder; şema doğrulaması reddi.
- **Gözlemlenebilirlik:** Tüm RPC çağrıları `out/replay.jsonl`'a yazılır; replay ile yeniden oynatılabilir.
- **Güvenlik:** RPC yalnız `127.0.0.1`, rastgele token (add-in başlarken üretilir, dosyaya yazılır).
- **Backend soyutlaması:** `Backend` arayüzü (`apply_ops`, `read_back`, `export_ifc`); `RevitBackend` ve `IfcBackend` aynı Op listesini tüketir.

## Hata modları
| Durum | Davranış |
|---|---|
| Revit açık değil | `get_status` açık hata; `dry_run` yine çalışır |
| Op başarısız | Rollback, hata op id + Revit mesajıyla döner |
| Revit uyarı penceresi | `FailuresPreprocessor` ile uyarı toplanır, modal pencere bastırılır |
| Spec geçersiz | Revit'e hiç gitmeden `validate_spec` reddeder |
