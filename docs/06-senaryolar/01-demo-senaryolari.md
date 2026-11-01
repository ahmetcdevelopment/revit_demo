# 01 · Demo Senaryoları ve Video Planı

## Senaryolar
### S-A · Altın yol (ana demo)
1. Claude'a: *"Konya Karatay Sarıyakup 20677 ada 13 parsele bitişik nizam 3 katlı apartman yap."*
2. `load_parcel` → parsel çizimi; `check_zoning` → çekmeler, yapılaşma alanı, TAKS/KAKS tablosu (atıflı).
3. `plan_building` → BuildingSpec; `validate_spec` → testler yeşil.
4. `build_in_revit(dry_run)` → "412 op, 3 kat, 6 daire" özeti; ardından `apply`.
5. Revit'te model oluşur (zaman atlamalı kayıt). `verify_model` → readback yeşil.
6. `export_ifc` → IDS raporu; tarayıcı viewer'da gezinme (stretch).

### S-B · İdempotency / değişiklik
"Kat yüksekliğini 3,00'dan 2,90 m'ye düşür." → diff: yalnız etkilenen elemanlar güncellenir; `verify_model` yeşil. İkinci aynı komut: "0 değişiklik".

### S-C · İhlal yakalama
"Bina 4 kat olsun." veya "Ön bahçe 2 m olsun." → imar motoru FAIL (KAT, KAKS, HMAX) + madde atfı; `build_in_revit` plan hatalıysa reddeder (`blocked`), Revit’e gitmez. "Ön bahçe 2 m" ise PAİY M23 varsayılanı plan notuyla aşılabildiği için `warn` döner (kasıtlı). Gösterir: denetim katmanı gerçek.

### S-D · Hata güvenliği
Bilerek bozuk op → rollback; model değişmedi; hata mesajı op id ile.

### S-E · Belgeden veri (stretch)
Örnek imar durumu PDF'i → Claude `ZoningParams` çıkarır → şema doğrulaması → eksik alan için soru. (Demo PDF'i sentetik olacaksa **"örnek belge"** diye etiketlenir.)

### S-F · Cephe detayı
Yakın plan klinker cephe (tuğla+derz), LOD anahtarı ve üçgen sayısı.

## Video (≤ 5 dk) — kare planı
| Süre | İçerik |
|---|---|
| 0:00–0:25 | Problem ve hedef; "LLM tarif eder, derleyici kurar" tek cümle |
| 0:25–1:15 | Mimari diyagram (README'den), repo gezintisi (klasörler) |
| 1:15–2:15 | S-A: prompt → parsel → imar raporu |
| 2:15–3:15 | Revit'te uygulama + readback testleri |
| 3:15–3:45 | S-B (idempotency) ve S-C (ihlal) |
| 3:45–4:30 | Klinker cephe, IFC/IDS sonucu |
| 4:30–5:00 | Sınırlar (dürüstlük): neyi doğruladım, neyi varsaydım; sonraki adımlar |

## Sık sorulan sorular (soru → kısa cevap)
- Neden MCP + spec derleyici? → determinism, test, idempotency.
- Revit thread'i? → ExternalEvent + kuyruk + TCS.
- Neden tek mesh tuğla? → eleman sayısı/performans.
- İmar doğruluğu? → belge-kaynaklı parametre, madde atıflı kural, `verified` bayrağı.
- Ölçek? → backend arayüzü, op log, çoklu proje için spec içerik adresleme.
- Sınırlar? → MEP/yapısal yok, tek parsel, demo varsayımları etiketli.

## Çekim önkoşulları
OBS kurulu · Revit açık, boş şablon · `out/` temiz · tüm fixture'lar donmuş · 2 prova.
