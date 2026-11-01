# 01 · Vizyon ve Kapsam

## Görev
Amaç, aşağıdaki herkese açık LinkedIn gönderisinde (Ramazan Güven, Claude↔Revit) anlatılana benzer bir sistemi kurmak. Teslim biçimi: **sunum + kod reposu + çalışma mantığı anlatımı** (canlı ortam gerekmez).

Kaynak (ilham ve atıf): https://www.linkedin.com/feed/update/urn:li:activity:7500106839041441792/

Gönderinin iddiaları (referans çıta):
1. Claude ile Revit arasında doğrudan köprü; elle çizim yok, komutla modelleme.
2. Gerçek parsel (Konya, Karatay, Sarıyakup, Genç Sokak, 20677/13): köşe koordinatları sisteme tanımlı.
3. İmar motoru: yönetmelik + plan notlarına göre çekme mesafesi, inşaat alanı.
4. Test motoru: üretilen modelin doğruluk/tutarlılık denetimi.
5. Bitişik nizam 3 katlı apartman: kütle, kat planı, cepheler.
6. Gerçek klinker tuğla cephe: tuğla + harç payı + örgü düzeni.
7. Ortak merdiven kovası, her katta 2 bağımsız daire girişi, mahaller (salon, yatak odası, banyo, WC).
8. 2D ruhsat projesi → IFC (yeni BIM yönetmeliği).
9. Belgeden veri aktarımı (imar durumu, tapu, kroki).

## Bizim hedefimiz
Çıtayı **aşan** bir versiyon: aynı sonuçlar + (a) deterministik, test edilebilir mimari, (b) kanıtlanabilir uygunluk (IDS ile IFC doğrulama), (c) tarayıcıda gezilebilir model, (d) kuralların madde atıflı olması.

## Kapsam (MVP — Cuma'ya mutlaka)
- [M1] Parsel poligonu (gerçek TKGM koordinatı veya sabitlenmiş fixture) → yerel metrik düzlem.
- [M2] İmar motoru: kenar bazlı çekme, yapılaşma alanı, TAKS/KAKS/Hmax kontrolü, madde atıflı rapor.
- [M3] BuildingSpec üretimi: 3 kat, bitişik nizam, ortak merdiven, kat başına 2 daire, mahaller.
- [M4] Revit add-in: köprü + Level, Wall, Floor, Roof, Room, Door, Window, Stair op'ları; transaction güvenliği.
- [M5] Model üzerinde test motoru (readback) + offline testler.
- [M6] IFC4 export + IDS doğrulama raporu.
- [M7] Klinker cephe (panel başına tek mesh, derz dahil).
- [M8] README, mimari diyagram, video.

## Kapsam dışı (şimdilik)
MEP/yapısal disiplinler, nokta bulutu→BIM, tam otomatik pafta üretimi, 2D DXF→IFC (stretch), çok parselli ada analizi, kullanıcı arayüzü (UI) uygulaması.

## Stretch (zaman kalırsa, sırayla)
S1 tarayıcı IFC viewer · S2 belge (PDF) → ImarDurumu çıkarımı demosu · S3 2D DXF → IFC · S4 pafta/şemalar (sheet) üretimi.

## Başarı ölçütleri (Definition of Done — proje)
- [ ] `pytest` yeşil, Revit'siz çalışır (CI'da da).
- [ ] Tek komutla (MCP aracı) parselden Revit modeline gidiliyor.
- [ ] Aynı spec iki kez uygulanınca ikinci çalıştırma **0 değişiklik** üretir (idempotent).
- [ ] Revit'ten readback testleri geçer; uyarı sayısı raporlanır.
- [ ] IFC4 dosyası IDS kontrolünden geçer.
- [ ] Her imar kuralı ihlali/uyumu maddesine atıf verir.
- [ ] Video 5 dk altında, repoyu ve mantığı anlatır.

## Dürüstlük kuralları (pazarlık dışı)
1. Sayısal imar eşikleri **doğrulanmamışsa** kod içinde `verified: false` olarak işaretlenir ve raporda "varsayım" yazar. Hafızadan kesin değer gibi sunulmaz.
2. Revit'te çalıştırılmamış kod "test edildi" diye sunulmaz.
3. Parselin gerçek imar durumu belgesi elde yoksa demo parametreleri açıkça "demo varsayımı" diye etiketlenir.
4. Başkasının gönderisinden birebir kopya iddiası yapılmaz; ilham kaynağı belirtilir.
