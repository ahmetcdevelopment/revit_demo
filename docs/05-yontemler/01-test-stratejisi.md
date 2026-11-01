# 01 · Test Stratejisi

Üç katman. Üst katman pahalı ve az, alt katman ucuz ve çok.

## Katman 1 — Offline (Revit'siz, `pytest`, CI'da koşar)
| Alan | Testler |
|---|---|
| Şema | Geçerli/geçersiz spec fixture'ları; sürüm uyumsuzluğu; kararlı id; `spec_id` tekrarlanabilirliği |
| Parsel | Halka kapalı/saat yönü; alan farkı; mikro kenar; CRS dönüşümü bilinen noktalarla (köşe → metrik → geri) |
| İmar | Dikdörtgen parselde elle hesap; trapezoid sabit sonuç; çekme=0 ⇒ B=P; kenar bazlı farklı çekme; bitişik nizamda party kenar sınıra oturur; TAKS/KAKS sınır değerleri; `verified:false` kuralı "assumed" döner |
| Planlayıcı | Odalar çakışmaz, kapsama ≥ %98, bağlılık grafı (BFS), ıslak hacim hizası, party duvarda pencere yok, merdiven geometrisi tutarlı |
| Derleyici | Op sıralaması topolojik; döngü yok; her `spec_ref` bir spec öğesine işaret eder; deterministik (iki çalıştırma aynı JSON, bayt eşit) |
| Altın dosya | `tests/golden/*.json` — referans spec/op çıktıları; değişim bilinçli onayla güncellenir |
| Özellik tabanlı | (opsiyonel) rastgele dikdörtgen parseller için invariantlar: ayak izi ⊂ B, alan ≤ limit |

## Katman 2 — Model (Revit içinde, readback)
`verify_model` şunları karşılaştırır:
- Eleman sayıları (kat, duvar, döşeme, oda, kapı, pencere) spec ile birebir.
- Oda alanı beklenenle ±%2 (Room.Area).
- Duvar uzunlukları/kalınlıkları, kat kotları.
- Her elemanda `spec_id` mevcut; modelde spec'te olmayan "yetim" eleman yok.
- Uyarı (warning) sayısı: kritik uyarı = 0 (örn. "highlighted walls overlap"), diğerleri raporlanır.
- **Idempotency testi:** aynı spec ikinci kez `apply` → diff = 0.
- **Rollback testi:** bilerek bozuk op → model değişmez.

## Katman 3 — Dış doğrulama (IFC)
- IFC4 dosyası `ifcopenshell` ile açılır: IfcSite/Building/BuildingStorey hiyerarşisi, IfcWall/IfcSlab/IfcSpace sayıları.
- **IDS**: proje için yazılmış `data/rules/project.ids` (ör. her IfcWall'da `FireRating`/`IsExternal`, her IfcSpace'te `Name`+`NetFloorArea`, her IfcBuildingStorey'de `Elevation`) → `ifctester` çıktısı rapora girer.
- **Not:** "Yeni BIM yönetmeliğine uygun" iddiası için resmi gereksinimi (hangi yönetmelik/şartname, hangi IFC sürümü ve parametre seti) **araştırmadan** iddia etme. Görev P6-T01: ilgili düzenlemenin metnini bul (Çevre, Şehircilik ve İklim Değişikliği Bakanlığı BIM düzenlemesi), gereksinimleri IDS'e çevir; bulunamazsa README'de "genel IFC4/IDS profili; yönetmelik eşlemesi doğrulanmadı" yaz.

## Test verisi
`tests/fixtures/`: `parcel_rect.json`, `parcel_trapezoid.json`, `parcel_karatay.json` (gerçek/dondurulmuş), `zoning_demo.json`, `spec_valid.json`, `spec_invalid_*.json`.

## Kabul kapıları (her faz sonunda)
Faz çıktısı için `pytest -q` yeşil + faz DoD kontrol listesi + `PROGRESS.md` güncel. Kapı geçilmeden sonraki faza geçilmez (kesme çizgisi hariç).

## Raporlama
`out/test-report.md`: kaç test, hangi katman, readback özeti, uyarı sayısı; README'ye rozet.
