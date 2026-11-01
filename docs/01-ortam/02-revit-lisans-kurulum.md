# 02 · Revit Lisans ve Kurulum Planı

## Bulgular (2026-10-28, web araştırması)
- Autodesk, Revit için **30 günlük ücretsiz deneme** sunuyor ("Try Revit free trial for 30 days"). Deneme sürümü sonradan uzatılamaz. İndirme boyutu sayfada **16 GB'a kadar** diye belirtiliyor.
- **Kart gerekliliği DOĞRULANAMADI.** Sayfa metni bunu açıkça yazmıyor; bölgeye göre değişebilir ve bir kaynak "ödeme yöntemi istenmediyse deneme otomatik biter" diyor. **Kullanıcı kayıt sırasında kart ister mi, kendisi görecek.** Kart istenirse: DURUR, devam etmeyiz (para harcama yok).
- **Education planı:** Uygun öğrenci/eğitmenler için ücretsiz, tek kullanıcı, **1 yıl, yıllık yenilenebilir**; doğrulama SheerID ile (okul e-postası/belge). Bölge uygunluğu resmi sayfadan kontrol edilmeli. Eğer kullanıcı öğrenci/öğretmen ise **en iyi seçenek budur** (30 gün sınırı yok).
- Autodesk sitesi Türkiye'ye yönlendirme sunuyor ("Türkiye sitemizi ziyaret edin"); deneme sayfası ABD sitesinde açıldı. Hesap bölgesi sorun çıkarırsa TR sitesi denenir.
- Güncel Revit: **Revit 2027** (.NET 10). Deneme sürümü indirme ekranında sürüm seçimi sunuluyor olabilir; **hangi sürümlerin seçilebildiği doğrulanmadı**.

Kaynaklar: autodesk.com/products/revit/free-trial · autodesk.com/education/home · blog.autodesk.io (Revit 2027 SDK)

## Karar ağacı
```
Kullanıcı öğrenci/eğitmen mi?
 ├─ Evet → Education planı (SheerID) → Revit 2027 (veya sunulan sürüm) indir
 └─ Hayır → 30 gün deneme
        ├─ Kart istemiyor → kur (deneme sayacı kuruluma değil ilk açılışa bağlı olabilir: kontrol et)
        └─ Kart istiyor → DUR → kullanıcıya bildir → Yedek (IfcBackend, karar D14)
```

## Kurulum görevleri (kullanıcı yapar, ajan kılavuzlar)
1. Disk boş alanını ölç (≥ 40 GB önerilir).
2. Autodesk hesabı → deneme/Education → indir (Autodesk Access / Install Now).
3. **Kurulumu bu akşam başlat**, arka planda bırak.
4. Kurulum sonrası: Revit'i bir kez aç, boş şablon yükle, `Help > About` sürüm numarasını not et → `PROGRESS.md`.
5. Deneme sayacını Cuma çekimine kadar yetecek şekilde yönet: **video çekimi ve test günleri 30 gün içinde.**

## Sürüm → .NET eşlemesi
| Revit | .NET | Not |
|---|---|---|
| 2027 | .NET 10 (SDK 10.0.100+, `global.json` rollForward minor) | All-Users add-in konumu `ProgramData`'dan `Program Files`'a taşındı → biz **kullanıcı bazlı** `%AppData%\Autodesk\Revit\Addins\2027` kullanırız |
| 2025 / 2026 | .NET 8 | Eski sürüm gelirse `TargetFramework` değişir |
| ≤ 2024 | .NET Framework 4.8 | Beklenmiyor |

Add-in'in `TargetFramework`'ü kurulan sürüme göre P3'te sabitlenir (karar D07).

## Revit'siz derleme
Revit API'si NuGet'ten (`Nice3point.Revit.Api.RevitAPI` / `RevitAPIUI`, 2027.x paketleri mevcut) alınır; böylece kurulum bitmeden add-in iskeleti derlenir. Çalıştırma/doğrulama ise Revit gerektirir.
