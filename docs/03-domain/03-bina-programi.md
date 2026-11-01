# 03 · Bina Programı

## Tipoloji
**Bitişik nizam, 3 katlı apartman**, her katta **iki daire**, ortak **merdiven kovası** (iki daireye hizmet), her katta bağımsız daire girişi. Kat adedi imar durumundan (demo: 3).

## Program tablosu (demo varsayımı — parsel ölçüsüne göre ölçeklenir)
| Mahal | Tip | Hedef alan (m²) | Not |
|---|---|---|---|
| Salon | living | 20–28 | cepheye bakar (ön veya arka) |
| Mutfak | kitchen | 8–12 | ıslak hacim şaftına komşu |
| Yatak odası × 2–3 | bedroom | 10–14 | |
| Banyo | bath | 4–5 | ıslak hacim şaftı |
| WC | wc | 1,5–2 | |
| Antre/hol | hall | 4–6 | giriş kapısı |
Gerçek asgari değerler PAİY/standart doğrulamasından (P1-T05) sonra `rules`'a girer.

## Yerleşim stratejisi (kural tabanlı planlayıcı)
1. **Kütle:** yapılaşma alanı B içinde dikdörtgen/çokgen ayak izi seç (parsel eğrisel değilse B'nin en büyük içsel dikdörtgeni; yoksa B'nin kendisi). TAKS/KAKS'a göre alan kısıtı.
2. **Aks sistemi:** sistematik kolon/aks yok (MVP'de taşıyıcı model yok); duvar eksenleri 5 cm modül.
3. **Çekirdek:** ortak merdiven kovası ayak izinin **orta/yan** bölümünde; boyutu iki kollu merdiven geometrisinden (kol genişliği, sahanlık) hesaplanır.
4. **Daire bölme:** çekirdeğin iki yanındaki iki bölge (A, B) → her biri bir daire; bitişik nizamda yan komşu duvarları (party) **kör**, pencereler yalnız ön ve arka cephede.
5. **Oda bölme:** her dairede önce "gündüz bölgesi" (salon+mutfak) ön/arkaya, yatak odaları diğer cepheye; ıslak hacimler çekirdek yanında topla (tesisat şaftı hizası tüm katlarda aynı).
6. **Açıklıklar:** daire girişi çekirdekten; oda kapıları; pencere genişlikleri cephe oranına göre; cephe modülüne (tuğla boyutu) oturtulan pencere genişlikleri.
7. **Katlar:** kat 0 (zemin) + kat 1–2; zemin katta giriş holü; çatı düz/teras (MVP) → stretch: beşik çatı.

Planlayıcı deterministiktir (girdi → aynı çıktı). Claude, plan parametrelerini (daire sayısı, yatak odası sayısı, çekirdek konumu tercihi) değiştirebilir; yerleşimi baştan çizmez.

## Offline invariantlar (planlayıcı çıktısı için)
- Odalar poligon olarak ayak izi içinde ve birbiriyle çakışmaz; kapsama ≥ %98.
- Her oda en az bir kapıyla bağlı; bağlılık grafı BFS ile tüm odalardan daire girişine ve oradan çekirdeğe ulaşır.
- Islak hacimler tüm katlarda aynı (x,y) şaftına hizalı.
- Cephe pencereleri yalnız `front/rear` duvarlarında; `party` duvarlarda yok.
- Merdiven kolu genişliği/basamak tutarlılığı; kat yüksekliği = n · rıht.
