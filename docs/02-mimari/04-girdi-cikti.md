# 04 · Girdi ve Çıktılar (kullanıcı gözüyle)

## Tek cümlelik tanım
Kullanıcı bir **parsel kimliği** verir (il, ilçe, mahalle, ada, parsel) ve doğal dille ne istediğini söyler. Sistem parseli kendisi bulur, imar uygunluğunu denetler, bina alternatifleri üretir, seçilenini Revit'te kurar, modeli doğrular ve rapor/IFC üretir.

## Girdiler
| # | Girdi | Kim sağlar | Zorunlu mu | Nasıl kullanılır |
|---|---|---|---|---|
| G1 | **Parsel kimliği** (il, ilçe, mahalle, ada, parsel) | Kullanıcı (bir cümle) | Evet | Sistem TKGM'den köşe koordinatlarını, alanı, niteliği otomatik çeker |
| G2 | **Komşuluk / yol bilgisi** | **Sistem (otomatik)** | — | Her kenarın dışı TKGM'den sorgulanır: komşu parsel = party kenar, parsel yok = yol/kamu alanı. Kullanıcı yalnız teyit eder |
| G3 | **İmar durumu belgesi** (PDF/fotoğraf) | Kullanıcı (belediyeden alınan resmi belge) | Önerilir | Claude belgeyi okur → TAKS, KAKS, kat adedi/Hmax, nizam, çekmeler. **Belge yoksa** PAİY varsayılanları kullanılır ve her sayı "varsayım" diye etiketlenir |
| G4 | **Tasarım isteği** (doğal dil) | Kullanıcı | Hayır | Örn. "3 katlı, kat başına 2 daire, klinker cephe". Verilmezse varsayılan program |
| G5 | Mevzuat | **Sistem (kalıcı kural kataloğu)** | — | PAİY ve Konya imar yönetmeliği, madde atıflı; parselden bağımsız, bir kez yazıldı |

**Neden G3 elle?** İmar durumu, belediyenin o parsel için verdiği **resmi belge**dir (TAKS, KAKS, kat adedi ve plan notları buradan gelir). Konya/Karatay için herkese açık, otomatik sorgulanabilir bir kaynak **bulamadım** (araştırma 2026-10-30). Bu yüzden belge sisteme **girdi olarak** verilir. Mimarlar da bu belgeyi her projede zaten ister; gönderideki sistem de "imar durumu, tapu, plan krokisi gibi dosyaların yüklenerek okunmasını" böyle anlatıyor. Her parsel için bir belge = tek manuel adım; geri kalan her şey otomatik.

## Çıktılar
| # | Çıktı | Biçim | İçerik |
|---|---|---|---|
| Ç1 | **İmar uygunluk raporu** | HTML/PDF | Parsel çizimi, kenar rolleri (komşu/yol kanıtıyla), yapılaşma alanı, TAKS/KAKS/kat adedi/çekme kontrolleri, her satırda madde atfı, varsayım damgaları, konum belirsizliği (±1 m) |
| Ç2 | **Alternatif karşılaştırması** | Tablo + plan çizimleri | Varyantlar: daire adedi, net/brüt alan, emsal kullanımı, verimlilik, doğal ışık; Claude'un yorumu ve önerisi |
| Ç3 | **BuildingSpec** | JSON | Seçilen bina; tek doğruluk kaynağı (deterministik) |
| Ç4 | **Revit modeli** | `.rvt` | Seviyeler, duvarlar, döşemeler, merdiven, mahaller (Room), kapı/pencere, çatı, klinker cephe |
| Ç5 | **Model doğrulama raporu** | JSON/HTML | Spec ↔ Revit geri okuma ↔ IFC: eleman sayıları, mahal alanları, uyarılar |
| Ç6 | **IFC4** | `.ifc` + IDS raporu | BIM uyumlu açık biçim |
| Ç7 | **Metraj** | Tablo | Alanlar, duvar/pencere/kapı listesi, tuğla adedi |
| Ç8 | **Görseller** | PNG | Revit'ten 3B ve plan görüntüleri (canlı demo olmadan kanıt) |

## Örnek kullanım (tek prompt)
> "Konya, Karatay, Büyüksinan, 1495 ada 26 parsel için bitişik nizam, 3 katlı konut alternatifleri üret; imar durumu ekte. En verimlisini Revit'te kur ve doğrula."

Sistem sırayla: parseli çeker → komşuları sorgular → belgeyi okur → imar kontrolü → alternatifler → seçilen Revit'e → doğrulama → rapor ve IFC.

## Neyi sistem yapar, neyi kullanıcı?
| İş | Sistem | Kullanıcı |
|---|---|---|
| Parsel koordinatı, alanı | Otomatik (TKGM) | — |
| Yol / komşu kenarlar | Otomatik (TKGM komşu sorgusu) | Gerekirse teyit |
| Yönetmelik kuralları | Otomatik (kural kataloğu) | — |
| İmar durumu sayıları | Belgeden okur | **Belgeyi verir** |
| Tasarım ve hesaplar | Otomatik | Tercih belirtir |
| Revit modeli, IFC, rapor | Otomatik | — |
