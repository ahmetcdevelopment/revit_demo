# P2 · Planlayıcı ve Derleyici (Revit'siz)

**Amaç:** Parselden `BuildingSpec`, ondan deterministik `Op` listesi.

| ID | Görev | Kabul |
|---|---|---|
| P2-T01 | Ayak izi seçimi (§2.2): yapılaşma alanından TAKS'a uyan dikdörtgen | ⊂ B, alan ≤ limit testi |
| P2-T02 | Kat tanımı ve yükseklikler; Hmax/kat adedi kontrolü | Seviye listesi |
| P2-T03 | Çekirdek (merdiven kovası) boyutlandırma ve konumlama; basamak hesabı | Rıht/basamak formül testi |
| P2-T04 | Daire bölgeleri A/B, oda bölme ağacı, ıslak hacim hizası | Çakışma yok, kapsama ≥ %98, hiza testi |
| P2-T05 | Duvarlar: dış (ayak izi), party, dahili, çekirdek; tekilleştirme | Kopya duvar yok |
| P2-T06 | Açıklıklar: giriş, oda kapıları, pencereler (party'de yok) | Kural testleri |
| P2-T07 | `validate_spec`: bütünlük (id/ref), bağlılık grafı, geometri kontrolleri | Geçersiz fixture'lar reddedilir |
| P2-T08 | Derleyici: Spec → Op (topolojik sıra, `depends_on`), `spec_id` içerik özeti | İki çalıştırma bayt eşit |
| P2-T09 | Altın dosyalar: `tests/golden/` | CI'da karşılaştırma |
| P2-T10 | `IfcBackend` taslağı: Spec → IFC (yedek yol, D14): Site/Building/Storey/Wall/Slab/Space | `ifcopenshell` ile açılıyor |

**DoD:** Karatay fixture'ından tam Spec+Ops üretiliyor; offline testlerin tamamı yeşil; IFC taslağı açılıyor (Revit'siz demo elimizde).
**Not:** T10, Revit riskine karşı sigortadır; basit tutulur (P6'da zenginleşir).
