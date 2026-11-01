# 04 · Kat Planı Tasarımı (Planlayıcı v2, kodlanmış hali)

Bu doküman `src/brain/planner.py`'nin yaptığını anlatır. Değişiklik gerekirse önce buraya yaz.

## Tipoloji: yol ucu başına bir blok
Gerçek parsel (Karatay / Büyüksinan 1495/26) ~70 × 17 m'lik bir şerit; iki ucu yola, iki uzun kenarı komşu parsellere açık (TKGM komşu sorgusu). Planlayıcı:
1. **Eksen:** komşu (party) kenarların uzunluk ağırlıklı yönü (−27.8°); parsel bu eksene döndürülür.
2. **Yol uçları:** `front` rolündeki (yol) kenarların hangi uçta olduğu bulunur → her uç için bir **blok**.
3. **Blok yerleşimi:** o uçtan başlayarak, yapılaşma alanına sığan en geniş eksen-hizalı dikdörtgen aranır (4 m'lik pencerede en geniş fit). Her blok kendi komşu sınırının yönüne göre yeniden hizalanır (bir iterasyon daha).
4. **Derinlik:** TAKS tavanından: `D = ⌊TAKS·alan / (W1+W2)⌋` (5 cm modül, 11.8–14.0 m arası). 
5. **Bloklar arası mesafe:** PAİY **Madde 24(2)**: her binanın yaklaşma mesafeleri toplanır → 3.00 + 3.00 = **6.00 m** (`PAIY-M24-BLOK-ARASI`). Gerçek parselde 17.6 m kalıyor.
6. **Party tespiti:** blok yan yüzü, komşu sınırından ≤ 0.6 m ise bitişik (party) sayılır; mesafe `BlockInfo.gap_*_m` ve `derived.party_gap_max_m`'e yazılır (şu an ≤ 0.29 m). > 0.6 m olan yüz cephe duvarı olur ve `known_gaps`'e düşer.

## Blok planı (u = cephe boyunca, v = yoldan içeri)
```
 v=0   ┌─ salon ──────┬bed1┤ çekirdek │ bed1 ┬────── salon ─┐ ← yol cephesi
       │              │    │ giriş holü│     │              │
       ├──────────────┴────┤ (sahanlık)├─────┴──────────────┤
       │ ───── hol (yatay) ─── │       │ ──── hol ───────── │
       │ banyo │ hol │ bed2    │MERDİVEN│ bed2 │ hol │ banyo│
       │ wc    │ dik │         │ (U)    │      │     │  wc  │
       │ mutfak│     │         │ arka   │      │     │mutfak│
 v=D   └───────┴─────┴─────────┴ çıkış ─┴──────┴─────┴──────┘ ← avluya bakan cephe
```
- **Çekirdek şeridi** (2.5 m): ön giriş → giriş holü/sahanlık → iki kollu merdiven → arka çıkış (avluya). Arka çıkış, Madde 4(1)(pppp)(2) "ortak alandan arka bahçeye çıkış".
- **Daire A (sol) / B (ayna)**: 2+1.
  - Ön sıra (yol cephesi, derinlik 4.4–6.0): **Salon** (genişlik ≈ wn−2.6−0.1) + **Yatak Odası 1** (2.6 m).
  - **Hol**: yatay şerit 1.30 m (çekirdek duvarındaki daire girişi buradan) + dik şerit 1.20 m (L biçimli, tek oda).
  - Arka bölge: ıslak sütun 2.2 m (**Banyo 1.9 m, WC 1.3 m, Mutfak** kalan derinlik), **Yatak Odası 2** (≥ 3.0 m).
- Duvarlar **elle çizilmez**: oda dikdörtgenleri arasındaki boşluk = duvar kalınlığı (0.10 bölme, 0.20 çekirdek, 0.25 dış/bitişik). Her bitişik oda çiftinden duvar çıkar (`A-SALON~A-HOL` gibi kararlı id), tutarsız boşluk/duvarsız temas `PlanningError` verir.
- Kapı/pencere konumu duvar parçasından türetilir; pencereler yalnız cephe duvarlarında (party'de **hiç** yok).

## Merdiven (iki kollu "U")
Kat yüksekliği 3.00 → rıht ≤ 0.16 (asansörsüz) → n = 19, r = 0.158; basamak b = 0.62 − 2r ≈ 0.30 (2a+b = 61.6 cm ∈ [60, 64], b ≥ 0.27); kol 1.20 m, kuyu 0.10, sahanlık 1.30; bölge uzunluğu 4.0 m. Kat döşemesi açıklığı: çekirdek genişliği × [vS+b, vS+4.0]. **Bilinen boşluk:** merdiven çatıya ulaşmıyor (M31(1)(b)).

## Düzeyler ve yüzeyler
L0 (0.00), L1 (3.00), L2 (6.00), R çatı (9.00, parapet 0.60). Blok başına her katta döşeme; L1/L2'de merdiven açıklığı; blok başına düz çatı.

## Sayılar (gerçek parsel, demo imar parametreleri)
2 blok (18.75 × 13.25 ve 18.0 × 13.25 m), kat başına 17 mahal/blok → 102 mahal, 216 duvar, 156 açıklık, TAKS 0.399, KAKS 1.197. `validate_spec` hatasız, uyarısız.

## Doğrulanmış mevzuat dayanakları
M23(1) bahçe mesafeleri · M24(2) birden fazla bina · M28 kat yüksekliği · M29 piyes asgarileri · M30(1) giriş koridoru · M31 merdiven · M32(1) yatak odası/oturma odası cepheden ışık alır. Hepsi `data/rules/paiy-2017.yaml`.

## Kasıtlı sadeleştirmeler / bilinen boşluklar
- Mevcut iki bina yok sayıldı (geometrileri bilinmiyor); yeni yapı bir **tasarım çalışması**.
- Pencere/aydınlatma alan oranı, yangın kaçış genişliği, otopark, sığınak, asansör kontrol edilmedi.
- Konya Büyükşehir İmar Yönetmeliği metni henüz kural kataloğuna işlenmedi (D20).
- Oda oranları algoritmik; mimari optimizasyon ve alternatifler (W3) sonraki adım.
