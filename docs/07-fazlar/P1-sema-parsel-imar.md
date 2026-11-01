# P1 · Şemalar, Parsel, İmar Motoru (Revit'siz)

**Amaç:** Projenin domain çekirdeği; tamamen test edilebilir.

| ID | Görev | Kabul |
|---|---|---|
| P1-T01 | TKGM'den 20677/13 parselini al (tarayıcıdan ağ çağrısı veya API); yanıtı `data/parcels/`'a dondur; CRS ve "ada/parsel" varsayımını doğrula | Fixture dosyası + kaynak notu; koordinatlar Konya aralığında |
| P1-T02 | `pyproj` ile EPSG eşlemesini sına (ITRF96/TM33 vb.), WGS84→metrik→yerel ENU dönüşümü ve geri dönüş testi | Gidiş-dönüş hatası < 1 mm |
| P1-T03 | Pydantic şemaları: ParcelSpec, ZoningParams, ZoningReport, BuildingSpec (başlangıç), Op | `pytest` şema testleri; JSON Schema export |
| P1-T04 | `parcel` modülü: yükle, normalize (CCW), doğrula, kenar rolleri (`edges_roles.yaml`) | Alan farkı testi; mikro kenar testi |
| P1-T05 | **Mevzuat doğrulaması:** PAİY güncel konsolide metin (mevzuat.gov.tr/Resmi Gazete) → ilgili maddeleri `data/rules/paiy-2017.yaml`'a atıfla işle; bulunamayanlar `verified:false` | Her kuralda `citation`; doğrulanmayanlar işaretli |
| P1-T06 | İmar durumu girdisi: gerçek belge elde yoksa `data/imar-durumu/demo.yaml` (`demo_assumption`); belge varsa PDF→ZoningParams elle/Claude ile | Kaynak türü açık |
| P1-T07 | `zoning`: kenar bazlı yapılaşma alanı, TAKS/KAKS/Hmax limitleri, `check_zoning` raporu | Dikdörtgen/trapezoid elle-hesap testleri |
| P1-T08 | Rapor: parsel+çekme SVG + kontrol tablosu HTML | `out/report.html` açılıyor, damga/atıf görünüyor |
| P1-T09 | Kenar durumları: eşkenar olmayan, içbükey parsel, çekme > parsel (boş B) | Anlamlı hata/uyarı |

**DoD:** `parcel_karatay` ile `check_zoning` çalışıyor; testler yeşil; kurallarda doğrulanmamış değer gizlenmiyor.
**Bağımlılık:** P0-T03, T05. **Riskler:** R05, R06, R07.
