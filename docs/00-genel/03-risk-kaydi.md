# 03 · Risk Kaydı

Olasılık/Etki: D(üşük) O(rta) Y(üksek). Takvim 2,5 gün olduğu için **takvim riski** merkezdedir.

| ID | Risk | O | E | Önlem | Tetik → Eylem |
|---|---|---|---|---|---|
| R01 | Revit denemesi kart istiyor / bölgede açılmıyor | O | Y | Education planı (uygunsa), alternatif hesap yolu; yedek `IfcBackend` | Perşembe 12:00'ye kadar Revit yok → yedek plana geç |
| R02 | Revit indirme/kurulum 16 GB'a kadar, saatler sürer | Y | O | **Hemen başlat**, arka planda; add-in NuGet ile Revit'siz derlenir | Kurulum çalışmıyorsa D14 |
| R03 | Revit 2027 add-in yükleme/izolasyon farkları (manifest konumu değişti) | O | O | Kullanıcı bazlı `%AppData%\Autodesk\Revit\Addins\2027` kullan | Add-in görünmezse manifest yolunu kontrol |
| R04 | Revit API tek thread; çağrı donması/çökme | O | Y | ExternalEvent + kuyruk, tek yazıcı, transaction timeout | Hata → TransactionGroup rollback |
| R05 | TKGM API belgesiz, 403/limit | O | O | Fixture dondurma (D12); elle koordinat | API cevap vermezse fixture |
| R06 | Konya/Karatay plan notları ve imar durumu belgesi elde yok | Y | Y | Parametreler "demo varsayımı" etiketiyle; belge yapısı hazır, değer girişi tek dosya | Gerçek belge gelirse yalnızca YAML/JSON güncellenir |
| R07 | Yönetmelik sayılarında hata (ikincil kaynaklar tutarsız) | Y | Y | `verified:false`, resmi metinle karşılaştırma görevi (P1) | Resmi metne erişilemezse varsayım etiketi |
| R08 | Merdiven kovası/oda yerleşimi geometrisi karmaşık | O | O | Parametrik, basit L-kolu/çift kollu merdiven; offline grafik testi | Süre aşılırsa tek kollu düz merdiven |
| R09 | Klinker cephe performansı | D | O | Panel başına mesh, LOD anahtarı | Yavaşsa derz detayını kapat |
| R10 | Kapsam şişmesi | Y | Y | Kesme çizgisi (aşağıda), stretch'e dokunma | Her faz sonunda kesme kararı |
| R11 | Ajan bağlam kaybı | O | O | CLAUDE.md + PROGRESS.md; her oturum başında okunur | — |
| R12 | Python yok → kurulum izni gerekir | Y | D | P0-T03; kullanıcıya komut verilir | — |

## Kesme çizgisi (zaman daralırsa bu sırayla at)
1. Stretch (S1–S4) → 2. Klinker cephe ayrıntısı (düz kaplama + doku) → 3. Mahal ayrıntıları (kapı/pencere sayısı sadeleşir) → 4. IDS (yalnızca temel IFC kontrolü) → 5. Rapor süsü.
**Asla kesilmez:** parsel+imar motoru, BuildingSpec, köprü, kütle/duvar/döşeme/oda, test motoru, README+video.
