# 05 · Plan v2 (2026-10-30) — gerçek parsel, Pazartesi teslim, yüksek doğruluk çıtası

## Durum değişikliği
- **Teslim: Pazartesi 2026-11-02** (saat belirsiz → hedef: Pazar 22:00'da donma, Pazartesi sabahı yalnız çekim/cila).
- **Gerçek parsel var:** Konya / Karatay / Büyüksinan (mahalleId 127989), **ada 1495 parsel 26**, tapu 1.220,51 m², kat mülkiyetli ("İki Adet Beş Katlı Apartman ve Arsası"), pafta 20M 4.
- Hedef kitle bir **mimarlık şirketi** → hesaplar denetlenebilir olmalı; sayılar kaynağına bağlanmalı; belirsizlik gizlenmemeli.
- Revit 2027 kurulu.

## Parsel analizi (TKGM, 2026-10-30; kanıtlı)
Geometri ~70 × 17 m çapraz şerit, 11 köşe, dışbükey değil. Komşu bulma yöntemi: her kenarın 3 m dışında, kenar boyunca 3 noktada TKGM koordinat sorgusu (`parsel/{lat}/{lon}/`).

| Kenar | Uzunluk | Dışında ne var? | Çıkarım |
|---|---|---|---|
| 0, 1 | 14.6 + 21.8 | parsel 1495/23 (Arsa, 809 m²) | **komşu** (güney) |
| 2, 3, 4 | 9.9 + 11.5 + 7.8 | parsel 1495/20 (Arsa, 591 m²) | **komşu** (güney) |
| 5 | 17.9 | 3–14 m boyunca parsel yok; 20 m'de 20918/2 | **kamu alanı, ≥ 15 m** (geniş yol/park?) — *kullanıcı teyidi bekliyor* |
| 6, 7 | 16.9 + 26.7 | parsel 1495/13 (Arsa, 488 m²); 7'nin ucu 1495/14 | **komşu** (kuzey) |
| 8 | 21.0 | parsel 1495/14 (Arsa, 477 m²) | **komşu** (kuzey) |
| 9, 10 | 8.3 + 10.3 | 3 m'de parsel yok; 6 m'de 1495/22 (13 katlı karkas apartman, 4.177 m²) | **kamu alanı, yol ≈ 3–6 m** (kullanıcı: "9, 10'da yol var") |

Sonuçlar:
1. Parsel **iki ucundan kamu alanına**, **iki uzun kenarından komşu parsellere** açık → bitişik nizam için doğal tipoloji: yol cepheleri kısa uçlar, party duvarlar uzun kenarlar. Uzun kenarlarda aydınlık yalnız iki uçtan gelir → derin bir plan, **ışıklık/hava bacası** gerekir (PAİY M32).
2. Batıdaki yol dar görünüyor (≈ 3–6 m; koordinat hassasiyeti ≈ 1 m). Konya Büyükşehir İmar Yönetmeliği Madde 9, kat adedini **yol genişliğine bağlayan** bir tablo içeriyor (planda kat adedi belirtilmemişse; örn. dar yollarda çok az kat). **Gerçek kat adedi imar durumundan gelmeli**; bu, tasarım kararını doğrudan etkiler.
3. Koordinatlar 5 ondalık derece (≈ 0.5–1 m) → sınırlarda **±1 m belirsizlik**. Alan farkı %0.24 (1223.42 hesap / 1220.51 tapu). Raporlarda bu belirsizlik açıkça yazılacak; kesin uygulama için aplikasyon krokisi gerekir.
4. Parsel şu an dolu (iki mevcut bina). Yeni bina "tasarım çalışması / alternatif" olarak sunulacak; mevcut yapı geometrisi bilinmiyor, modellenmeyecek.

## Yeni bilinen yerel mevzuat
**Konya Büyükşehir Belediyesi İmar Yönetmeliği** (RG 17.04.2026, sayı 33227): Büyükşehir sınırlarındaki uygulama imar planlı alanlar. Madde 23 bahçe mesafeleri PAİY ile aynı sayılar (5/3/3; 4 kattan sonra +0.50), ek olarak yol genişliğine bağlı kat adedi tablosu (Madde 9), çıkma/emsal dışı hükümleri (Madde 22), cephe/estetik komisyonu (Madde 26). **Şu an yalnız bir özet okundu (ikincil, doğrulanmamış);** P1-T05 gibi metin tam okunup kural kataloğuna `konya-imar-yonetmeligi.yaml` olarak işlenecek (Karatay'ın kapsamda olduğu doğrulanacak).

## En kritik girdi: imar durumu
Parselin **TAKS, KAKS, Hmax/kat adedi, nizam, çekmeler** yalnızca imar durumu belgesinden / plan notlarından gelir; bulamadım. Kaynak: Karatay Belediyesi veya Konya Büyükşehir Belediyesi imar durumu (belge veya e-sorgu). Elinde olması → rapordaki "DEMO VARSAYIMI" damgası kalkar, mimarlık şirketi için en büyük güven farkı bu. Yoksa tüm parametreler etiketli varsayım kalır.

## Kalite çıtası (kusursuza en yakın, dürüst tanım)
"Kusursuz" = *kanıtlanabilir doğru*. Şu kapıların hepsi geçmeden "bitti" denmez:
- **K-A Çift hesap:** Kritik sayılar (alan, TAKS/KAKS, çekme poligonu, merdiven ölçüleri) iki bağımsız yoldan hesaplanıp karşılaştırılır (ör. shapely ↔ elle-yazılı shoelace; spec ↔ Revit okuması ↔ IFC).
- **K-B Üç yönlü eşitlik:** `BuildingSpec` ↔ Revit geri okuma ↔ IFC: eleman sayıları, mahal alanları (±%1), duvar uzunlukları.
- **K-C Kaynak zinciri:** Raporda her değer kaynağıyla (TKGM sorgusu + zaman, PAİY/Konya madde no, plan notu) görünür; kaynağı olmayan "varsayım" der.
- **K-D İdempotency + rollback** Revit'te sınanmış.
- **K-E Negatif testler:** bilerek bozulan girdiler (4 kat, çekme ihlali, küçük oda) doğru reddedilir.
- **K-F Temiz klon:** sıfır bir klasörde `uv sync && pytest` ve README adımları çalışır.
- **K-G Belirsizlik beyanı:** konum ±1 m, plan notu yok, çatı merdiveni yok, vb. "Sınırlar" sayfasında.

## Planlayıcı v2 (gerçek parsel için zorunlu)
Mevcut planlayıcı 14 m'lik dar cepheli, tek çekirdekli, ≤ 12 m derin, dışbükey alan varsayıyor. Gerçek parsel için:
1. **Çok kenarlı cephe:** kenar 9+10 tek "ön cephe" doğrusu (en küçük kareler/uzun kenar yönü) olarak ele alınır.
2. **Dışbükey olmayan yapılaşma alanı:** yarı-düzlem kesişimi + dikdörtgen arama (ızgara/morfolojik); sonuç yine `largest_rect` mantığıyla doğrulanır.
3. **Derin plan tipolojisi:** ~16.5 × 28 m ayak izi → ortada çekirdek + ışıklık, ön daire (yol cephesi) ve arka daire (doğu cephesi), kat başına 2 geniş daire (3+1 / 4+1) **veya** 4 küçük daire (alternatif). Mahal asgarileri PAİY M29.
4. Alternatif üretimi ve sıralama (aşağıda W3).
5. Eski sentetik parsel testlerde regresyon fixture'ı olarak kalır.

## Etkileyici katmanlar (öncelik · tahmini efor · dürüst sınır)
| ID | Özellik | Neden etkileyici | Efor | Öncelik |
|---|---|---|---|---|
| W1 | **Kaynak zinciri / kanıt paneli** (rapor + MCP) | Mimar her sayının nereden geldiğini görür | 2 sa | Şart |
| W2 | **Veriden kenar rolü çıkarımı** (TKGM komşu sorgusu; yukarıdaki tablo) | Tahmin yok, kanıt var | yapıldı | Şart |
| W3 | **Alternatif üretim ve sıralama:** N plan varyantı; metrikler (net satılabilir alan, emsal kullanımı, verimlilik = net/brüt, doğal ışık cephesi, bağımsız bölüm adedi); Claude seçenekleri MCP ile karşılaştırıp önerir, seçileni Revit'e kurar | "AI tasarım ortağı", yalnız çizim aracı değil | 6–8 sa | Yüksek |
| W4 | **Üç yönlü metraj/tutarlılık:** spec ↔ Revit ↔ IFC alan/hacim/adet; tuğla adedi, duvar/pencere listesi | "Hesaplar tutuyor" kanıtı | 3 sa | Yüksek |
| W5 | **Güneş/gölge analizi:** Konya enlemi için güneş yolu, kış gündönümü cephe güneşlenmesi, **komşu parsellere gölge** (shapely + güneş vektörleri) | Mimari değer, görsel | 4–6 sa | Orta |
| W6 | **Revit paftaları:** otomatik kat planları + mahal cetveli + 3B görünüm + PDF dışa aktarım | Teslim edilebilir çıktı | 5–8 sa | Orta (risk: şablon/başlık bloğu) |
| W7 | **Belgeden veri (imar durumu PDF → ZoningParams)** + eksik alan soruları | Gönderideki iddiayı karşılar | 3 sa | Belge gelirse |
| W8 | **Revit'ten ekran görüntüsü/3B render'ı rapora** | Canlı demo olmadan kanıt | 2 sa | Orta |
| W9 | **IDS ile IFC doğrulama** + BIM yönetmeliği eşlemesi | Resmi uygunluk | 4 sa | Orta (yönetmelik araştırmasına bağlı) |

Öneri paketi: **Şart (W1, W2) + W3 + W4 + W8**, zaman kalırsa **W5**, belge gelirse **W7**; W6 ve W9 stretch.

## Takvim (Cuma → Pazartesi)
| Zaman | Hedef |
|---|---|
| **Cuma 30 (kalan)** | Plan v2 onayı · kenar rollerini kayda al · Konya yönetmeliği kural kataloğu · planlayıcı v2 başlangıcı (çok kenarlı cephe, dışbükey olmayan alan) |
| **Cumartesi 31** | Planlayıcı v2 bitiş + alternatifler (W3 çekirdeği) · **P3 Revit köprüsü** (RPC, ExternalEvent, transaction) · ilk Revit modeli (seviye/duvar/döşeme) |
| **Pazar 1** | P4 (merdiven, oda, kapı/pencere, çatı) · readback + idempotency · klinker cephe · IFC + metraj · MCP sunucusu · **Pazar 22:00 kod donar** |
| **Pazartesi 2** | Rapor/README/mimari anlatım · video · temiz klon testi · teslim |
Kapılar: K1 (Cumartesi akşam): Revit'te kütle + duvar var mı? Yoksa IfcBackend yedeği vurgulanır. K2 (Pazar akşam): tam model + readback yeşil mi?
