# 02 · Geometri Yöntemleri

## 2.1 Yapılaşma alanı (kenar bazlı çekme)
Bkz. `03-domain/02-imar-kurallari.md`. Uygulama: her kenar için iç yönde `d_i` kaydırılmış doğru → yarı-düzlem; kesişim `shapely` ile `Polygon.intersection`. Köşe dejenerasyonu: `buffer(0)`, minimum alan eşiği.

## 2.2 Ayak izi seçimi
- B dışbükeyse: B'nin içine yerleşen **en büyük eksen hizalı (veya ön cepheye paralel) dikdörtgen** — ön kenar yönünde döndürülmüş koordinatta ızgara aramasıyla (adım 5 cm), TAKS limitine kırp.
- B dışbükey değilse: dikdörtgen yaklaşımı; sonuç B'nin içinde olmalı (test).
- Bitişik nizam: ayak izinin `side_party` kenarına denk gelen yüzü parsel sınırına yapışık.

## 2.3 Duvar ve döşeme
- Dış duvar ekseni: ayak izi poligonunun içe doğru yarı-kalınlık kaydırması (cephe yüzü = ayak izi çizgisi); `walls[]` bu eksenden üretilir.
- Dahili duvarlar oda sınırlarından türetilir; ortak kenar tek duvar olur (tekilleştirme: aynı iki köşe → tek `wall`).
- Döşeme: kat ayak izi poligonu − merdiven açıklığı; kalınlık 0,20 m (varsayım).

## 2.4 Merdiven kovası
İki kollu (U) merdiven:
- Kat yüksekliği `H` → basamak sayısı `n = round(H / rıht_hedef)`, gerçek rıht `r = H/n`; basamak derinliği `b` için `2r + b ≈ 0,62–0,64` (doğrulanacak) ile seçilir.
- İki kol: her biri `n/2` basamak; ara sahanlık derinliği ≥ kol genişliği.
- Kova plan boyutu: `(2 · kol_genişliği + kol_arası) × (kol_uzunluğu + sahanlık)`.
- Revit'te: `StairsEditScope` + iki `StairsRun` + `StairsLanding`; başarısız olursa tek kollu düz merdiven (kesme çizgisi R08).
- Offline: geometri formülleri ve açıklık poligonu test edilir; Revit'te readback ile basamak sayısı/rıht doğrulanır.

## 2.5 Oda bölme
Dairenin bölgesi → "bölme ağacı" (slicing tree): önce gündüz/gece bölgesi, sonra odalar. Hedef alanlara oransal kesim; her kesimde minimum kısa kenar kontrolü. Çıktı: oda poligonları, kapılar için komşuluk grafı.

## 2.6 Açıklıklar
- Kapılar: iki oda arası ortak duvarın uygun bir noktasında; giriş kapısı hol–çekirdek duvarında.
- Pencereler: yalnız ön/arka cephede; cephe modülüne oturan genişlik; alt kot (sill) ve yükseklik sabit tablolar.
- Çakışma: bir duvarda açıklıklar arası ve köşeye en az 0,3 m.

## 2.7 Klinker tuğla cephe
- Tuğla boyutu (varsayılan, ayarlanabilir): 240 × 52 × 115 mm, derz 10 mm. Örgü: yarım taş kaydırmalı (stretcher bond).
- Cephe paneli = (cephe duvarı × kat). Tuğla ızgarası pencere/kapı boşlukları çıkarılarak kurulur (boşluk dikdörtgenleri + derz payı).
- Her tuğla bir kutu (8 köşe, 12 üçgen); satır başına yarım kayma; köşede yarım tuğla.
- **Performans:** Bir cephe ≈ onbinlerce tuğla → tüm tuğlalar **tek mesh** (tek DirectShape); tuğla ve derz ayrı malzeme setleri. Eleman sayısı sınırlı kalır. LOD anahtarı: `brick_lod = full|simplified|texture`. Üçgen sayısını raporla.
- Offline test: tuğla sayısı = (net cephe alanı / (tuğla+derz alanı)) ± %2; boşluklarla çakışma yok.

## 2.8 Çatı
MVP: düz teras (parapet). Stretch: eğimli çatı (`FootPrintRoof`).

## 2.9 Toleranslar
Geometri toleransı 1 mm (metre cinsinden 1e-3); koordinatlar 3 ondalık; modül 5 cm.
