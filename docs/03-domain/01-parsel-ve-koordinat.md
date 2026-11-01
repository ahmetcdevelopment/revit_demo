# 01 · Parsel ve Koordinat

## Hedef parsel
Gönderi: **Konya / Karatay / Sarıyakup Mah. / Genç Sokak / ada 20677 parsel 13**. Not: Gönderide "20677/13" yazıyor; bunun **ada/parsel** olduğu varsayımı P1-T01'de TKGM'den doğrulanacak. Farklı bir parsel seçmek de serbest (kullanıcı kararı); sistem parsel-bağımsız.

## Veri kaynağı: TKGM (Parsel Sorgu / CBS)
Bulgular (araştırma, 2026-10-28; **resmi dokümantasyon bulunamadı**):
- Halka açık arayüz: `https://parselsorgu.tkgm.gov.tr/`
- Topluluk istemcilerinin (QGIS eklentisi `okansafak/qgistkgmplugin`) kullandığı uç nokta tabanı: `https://cbsapi.tkgm.gov.tr/megsiswebapi.v3.1/api`
- Parsel çağrısı kalıbı: `GET {base}/parsel/{mahalleId}/{adaNo}/{parselNo}` → **GeoJSON Feature**; Polygon; koordinat sırası `[lng, lat]`.
- Alanlar: `mahalleId, adaNo, parselNo, alan, nitelik, pafta, ilAd, ilceAd, mahalleAd, durum`.
- İdari yapı (il/ilçe/mahalle id'leri): `…/api/maksIdariYapi` altında.
- Yanıtta CRS belirtilmiyor → büyük olasılıkla WGS84 derece; **doğrulama**: değerler lon≈32.x, lat≈37.x aralığında mı? P1-T01.
- Kullanım kısıtı: limit aşımında HTTP 403; belgesiz API, **değişebilir/engellenebilir** (karar D12).

### Yöntem (sırasıyla dene)
1. Tarayıcıda parselsorgu.tkgm.gov.tr üzerinden parseli bul; geliştirici araçları/ağ çağrısından gerçek yanıtı gör (yalnız tek parsel, hafif kullanım).
2. API cevap veriyorsa `tools/fetch_parcel.py` ile bir kez çek, `data/parcels/<id>.geojson` olarak **dondur**.
3. Erişilemezse koordinatları elle `data/parcels/<id>.manual.json` ile gir (kaynak notu zorunlu).
Demo her zaman fixture'dan çalışır.

## Koordinat sistemleri
- TKGM: WGS84 (EPSG:4326) olması beklenir (doğrulanacak).
- Türkiye ulusal: **TUREF (ITRF96 tabanlı) / TM 3° dilimleri**. `pyproj` ile doğrulandı (2026-10-28): EPSG:5253 = TUREF / TM27, 5254 = TUREF / TM30, **5255 = TUREF / TM33**. Konya (≈32,5°E) 31,5–34,5°E aralığındaki dilimde → **EPSG:5255**. Dilim seçimi P1-T02'de gerçek koordinatla (boylam) son kez sınanacak.
- Çalışma düzlemi: seçilen metrik CRS'e çevir → orijini ilk köşeye/ağırlık merkezine taşı → **yerel ENU**.
- Revit'te: Project Base Point/Survey Point + (IFC'de) `IfcMapConversion` ile georeferans; MVP'de yerel düzlem + not.

## Doğrulamalar (`validate_parcel`)
- Halka kapalı, kendini kesmiyor, saat yönü normalize.
- `|area_computed − area_tapu| / area_tapu < %1` (aksi: uyarı).
- Her kenar için uzunluk > 0.3 m (mikro kenar temizliği).
- En az bir `front` kenarı; bitişik nizamda en az bir `side_party`.

## Kenar rol ataması
Otomatik tahmin yok (güvenilmez). Girdi: `edges_roles.yaml` (kenar indeksi → rol, komşu durumu, yol adı/genişliği). Claude, fixture haritasını/krokiyi okuyarak öneri yapabilir; **insan onaylar** (bilinen en büyük belirsizlik kaynağı).
