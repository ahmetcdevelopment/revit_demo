# 02 · İmar Kuralları

## Hiyerarşi (hangisi hangisini ezer)
1. **Parselin imar durumu belgesi / plan notları** (Konya Büyükşehir / Karatay belediyesi) — *asıl kaynak*: nizam, TAKS, KAKS, Hmax/kat adedi, çekmeler.
2. **Planlı Alanlar İmar Yönetmeliği (PAİY)** — plan notlarında belirtilmeyen konularda genel hükümler.
3. Diğer: Yapı Denetimi, Binaların Yangından Korunması Hakkında Yönetmelik, Erişilebilirlik (TS 9111) vb. → MVP'de yalnız merdiven/mahal ölçüleri.

Bu yüzden `ZoningParams` bir **belgeden** gelir; kod gömülü sabit tutmaz.

## DOĞRULANDI (P1-T05, 2026-10-28) — resmi metinden
Kaynak: mevzuat.gov.tr resmi PDF (`https://www.mevzuat.gov.tr/MevzuatMetin/yonetmelik/7.5.23722.pdf`, 57 sayfa; metin RG-1/7/2026-33297 değişikliğine kadar işlenmiş). Kural kataloğu: `data/rules/paiy-2017.yaml` (`verified: true`). Bulgular:
- **Madde 23(1)**: planda aksine hüküm yoksa ön bahçe ≥ 5.00 m, yan bahçe ≥ 3.00 m, arka bahçe ≥ 3.00 m; 4 kattan fazla binada 4 üzerindeki her kat için yan/arka +0.50 m (3 katta uygulanmaz).
- **Madde 4(1)(pppp)(2)**: bitişik nizam tanımı · **(cccc)** TAKS tanımı · **(nnnn)** yan bahçe tanımı.
- **Madde 21(4)**: planda emsal verilmeyen parselde katlar alanı = TAKS × kat adedi. **Madde 22(1)(l)**: merdiven evi/balkon kısmen emsal dışı (kapsam yoruma açık → bizde muhafazakâr: sayılır).
- **Madde 28**: konut bölgesinde kat yüksekliği ≤ 3.60 m, bodrum hariç 3 katı geçmeyen binada ≤ 4.00 m (planda daha fazlası belirlenmemişse); iç yükseklik ≥ 2.60 m.
- **Madde 29**: piyes asgarileri (salon 12 m²/3.00; yatak 9 m²/2.50; mutfak 3.30 m²/1.50; banyo 3.00 m²/1.50; WC 1.20 m²/1.00; hol/koridor ≥ 1.20).
- **Madde 31**: ortak merdiven kolu/sahanlık ≥ 1.20 m; rıht ≤ 0.16 (asansörsüz) / 0.18 (asansörlü); 2a+b = 60–64 cm, basamak ≥ 0.27 m.
- **Madde 41**: çıkmalar 1.50 m; yan/arka sınıra 3.00 m'den fazla yaklaşmamak kaydıyla; bitişik nizamda komşu sınırına 2.00 m kuralı.
**Önemli sınır:** Bu değerler *varsayılan*dır. Parselin **imar durumu / plan notları** bunları değiştirebilir (özellikle TAKS, KAKS, Hmax, çekmeler). Bu yüzden `ZoningParams` parametreleri hâlâ belge kaynaklıdır; PAİY varsayılanlarından düşük değerler "UYARI" olur, hata olmaz.

## Eski bulgular (ikincil kaynak; yukarıdaki doğrulama ile değerlendirilmeli)
- PAİY, **03.07.2017 tarih, 30113 sayılı Resmi Gazete**; eski "Planlı Alanlar Tip İmar Yönetmeliği"nin yerini aldı. Birçok kez değişti (konsolide metin tarihleri farklı: 2025, 2026 sürümleri dolaşıyor).
- İkincil kaynaklarda **tutarsız** ifadeler: bitişik nizamda arka bahçe en az 3 m; yükseklik/kat arttıkça yan-arka bahçelere kat başına 0,50 m ekleme; komşu sınırına yaklaşma şartları. Bunlar **kesin değer olarak kullanılmayacak**.
- **Görev P1-T05:** mevzuat.gov.tr'den (veya Resmi Gazete) güncel konsolide metni oku; ilgili maddeleri (nizam tanımları, bahçe mesafeleri, çıkmalar, yükseklik, TAKS/KAKS tanımı, emsale dahil olmayan alanlar, merdiven/sığınak) `data/rules/paiy-2017.yaml`'a **madde numarası + tarih + tam atıfla** işle ve `verified: true` yap. Doğrulanamayan her kural `verified: false` kalır ve raporda "varsayım" görünür.

## Kural şeması (`data/rules/*.yaml`)
```yaml
- id: PAIY-BAHCE-ARKA-MIN
  title: "Bitişik nizam arka bahçe en az"
  applies_if: {nizam: bitisik}
  param: setbacks.rear
  op: ">="
  value: 3.0            # örnek; doğrulanana kadar verified:false
  unit: m
  citation: {doc: "PAİY", article: "?", gazette: "RG 30113", date: "2017-07-03"}
  verified: false
```
İki tür kural: **(a) parametre kuralları** (imar durumundan gelen değerler), **(b) genel kontroller** (merdiven kolu ≥ x, mahal alanı ≥ y). Her kontrol sonucu rapora `citation` ile döner.

## Hesap algoritması (yapılaşma alanı)
Girdi: parsel halkası P, kenar rolleri, çekme değerleri.
1. Her kenar `e_i` için, içe doğru `d_i = setback(role_i)` kadar **kaydırılmış yarı-düzlem** (offset line) oluştur.
2. Yapılaşma alanı B = P ∩ (tüm yarı-düzlemlerin kesişimi). (`shapely`: her kenar için `P.buffer` kullanma — kenar bazlı farklı mesafe gerekir.)
3. `side_party` kenarlarında d=0: yan duvar **parsel sınırına oturur**; komşu tarafın yangın duvarı kalınlığı ayrı parametre.
4. Köşelerde dar/dejenere sonuç → temizle (`buffer(0)`, minimum kenar eşiği).
5. Çıkmalar (balkon/cumba) ayrı poligon; çekmeye taşma kontrolü (`extras.cikma_max_m`).

Doğrulama: dikdörtgen parselde elle hesap, trapezoid parselde sabit sayısal test, çekme=0 durumunda B=P.

## Alan ve yükseklik
- **TAKS** = zemindeki (izdüşüm) kapalı alan / parsel alanı → `footprint_area ≤ taks · parsel_alani`.
- **KAKS (emsal)** = emsale dahil toplam inşaat alanı / parsel alanı. Emsale dahil olmayan alanlar (merdiven kovası, asansör, ortak alan oranları vb.) **mevzuattan doğrulanıp** `rules`'a girilecek; doğrulanana kadar tüm kat alanları emsale dahil sayılır (muhafazakâr) ve rapor bunu belirtir.
- **Hmax / kat adedi:** imar durumu; yoksa demo: 3 kat · kat yüksekliği 3,00 m (varsayım, etiketli).

## Merdiven ve mahal ölçüleri (MVP kontrolleri)
Kaynak (PAİY ve ilgili yönetmelikler) doğrulanana kadar `verified:false`: kol genişliği, rıht/basamak (2h+b ≈ 62–64 cm kuralı), sahanlık derinliği, korkuluk yüksekliği, minimum oda alanı/kısa kenar, ıslak hacim, pencere/alan oranı. Bu kontroller **uyarı** seviyesinde başlar; resmi metin işlenince **hata**ya yükseltilir.

## Rapor
`report.html`: parsel şeması (SVG), çekme çizgileri, yapılaşma alanı, kontrol tablosu (pass/fail/assumed + atıf), varsayım damgaları, kaynak belgeler.
