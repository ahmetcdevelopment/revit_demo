# P6 · IFC/IDS, Klinker Cephe, Rapor

| ID | Görev | Kabul |
|---|---|---|
| P6-T01 | Araştırma: Türkiye'de BIM/IFC gereksinimleri (Çevre, Şehircilik ve İklim Değişikliği Bakanlığı düzenlemesi, IFC sürümü/parametreler). Bulguları `docs/03-domain/04-bim-yonetmeligi.md`'ye yaz; bulunamazsa "doğrulanmadı" yaz | Notta kaynak bağlantısı |
| P6-T02 | Revit IFC4 export (`IFCExportOptions`), ayarlar | `.ifc` açılıyor |
| P6-T03 | Beyin tarafı IFC kontrol: hiyerarşi, sayılar | `ifcopenshell` testleri |
| P6-T04 | `project.ids` yaz; `ifctester` ile doğrula; rapor | IDS raporu `out/` içinde |
| P6-T05 | Klinker tuğla üreteci (Python, saf): boşluklu cephe → mesh üçgenleri; sayı ve alan testleri | Offline testler yeşil |
| P6-T06 | `create_brick_panel` op'u (C#): TessellatedShapeBuilder → DirectShape; malzeme | Revit'te görünür; üçgen sayısı raporlanır |
| P6-T07 | LOD anahtarı (`full/simplified/texture`) | Performans ölçümü |
| P6-T08 | Rapor birleştirme (`report.html`): parsel, imar, plan şeması, test sonuçları, IDS | Tek dosya, bağımsız |
| P6-S1 | (stretch) Tarayıcı IFC viewer (Vite + That Open) | Yerelde açılıyor |
| P6-S2 | (stretch) Belge→ZoningParams demosu | Senaryo S-E |

**Durum (2026-10-31): T01–T08 tamam (T01 kısmen: yönetmelik ekleri okunamadı). Revit IFC4 + IDS 10/10, klinker 41 882 tuğla, rapor `out/project-report.html`. S1 (tarayıcı 3B model) yapıldı, S2 yapılmadı. Ayrıntı: `PROGRESS.md`.**

**DoD:** IFC üretilip doğrulanıyor; cephe Revit'te klinker olarak görünüyor; rapor eksiksiz.
