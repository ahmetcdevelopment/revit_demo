# PROGRESS — Canlı Durum

Son güncelleme: 2026-10-28 (Çarşamba, gece) · Teslim: Cuma 2026-10-30

## Güncelleme (2026-10-30, Cuma)
**Revit 2027 kurulu** (`C:\Program Files\Autodesk\Revit 2027\Revit.exe`, build 20260907_1515); `%AppData%\Autodesk\Revit\Addins\2027` mevcut. Hedef `net10.0-windows` ile uyumlu → D07 kesinleşti. P3 için kullanıcı onayı bekleniyor. Teslim günü: parsel için sentetik ile devam önerildi.

## P7 (2026-11-01, Pazar): doküman + temiz klon testi YAPILDI; video ve teslim kullanıcıda
- ☑ T01 README yeniden yazıldı (Mermaid mimari, dürüstlük tablosu, hızlı başlangıç, sonuçlar). ☑ T02 mimari anlatım README + `docs/02-mimari`. ☑ T03 `docs/00-genel/04-dogrulama-tablosu.md` (neyi test ettim / neyi varsaydım). ☑ T05 metin hazır: `docs/06-senaryolar/02-video-senaryosu.md`.
- ☑ T08 temiz kopya (`.venv`, `out`, `.git` hariç): `uv sync` + `pytest` → 158 geçti, 1 atlandı; `dotnet build` 0 uyarı/0 hata; `plan_demo` ve `mcp_smoke` çalıştı. Yakalanan hata: `tools/make_report.py` `out/` yokken düşüyordu → düzeltildi.
- ☑ `tools/scenarios.py` yeniden koşuldu (Revit açık): S-A…S-F hepsi PASS, pytest 159 geçti → `out/test-report.md`, `out/project-report.html`.
- ☑ Sunum: `docs/sunum.pptx` (21 slayt: problem, referans çıta, boşluklar, karşılaştırma, maliyet, üstünlükler, 5 Mermaid diyagramı, parsel/plan/Revit/klinker/IFC-IDS/3B görüntüleyici, senaryolar, dürüstlük, ürünleşme). Konuşma metni slayt notlarında. Mermaid kaynakları `docs/diagrams/*.mmd`. Şema doğrulaması geçti, PowerPoint ile PNG'ye aktarılıp görsel kontrol edildi. Üretici betikler repoda değil (geçici klasör). Gönderi/video karşılaştırması yalnızca gönderi metnine dayanır; videonun kendisi ve diğer MCP projelerinin kodu incelenmedi.
- ☐ T04 ekran görüntüleri/GIF (`docs/assets/`), ☐ T06 video çekimi, ☐ T07 teslim (GitHub yayını kullanıcı onayı ister; commit hâlâ atılmadı). Parapet yapılmadı.

## Tarayıcıda gezilebilir 3B model (2026-11-01) — YAPILDI (P6-S1)
`uv run python tools/view.py --build` → `out/viewer/` (GLB + sahne + three.js) yerel sunucuda açılır; MCP aracı `export_viewer`. Revit'in IFC'sinden (`out/revit.ifc`, yoksa spec IFC'si): 809 eleman, 474 bin üçgen, GLB 10.8 MB, dönüştürme ~25 s.
- Özellikler: yörünge kamerası, Perspektif/Üstten/Ön, **kat aç-kapat**, **eleman grupları** (duvar, klinker, döşeme, kapı-pencere, merdiven, mahal hacimleri), **kesit kaydırıcısı**, duvarları saydamlaştır, gölge, **tıklayınca IFC bilgisi** (ad, sınıf, kat, GUID), **parsel + çekme çizgileri** (kenar rolü renkleri, kesikli yapılaşma alanı), imar göstergeleri, "DEMO VARSAYIMI" etiketi. Tarayıcıda (gerçek) denendi: yükleme, kat kapatma + kesit, tıklama.
- Bağımlılık: yalnız `three@0.170.0` (MIT, npm'den bir kez indirildi, `src/viewer/vendor/three` altına kopyalandı) → **internetsiz çalışır**; testle korunuyor (`tests/test_viewer_export.py`: dış URL yok, vendor tam, GLB geçerli, Y-yukarı, NaN yok).
- Tuzak: bazı Revit stilleri `NaN` saydamlık taşıyor → GLB JSON'u bozuyordu; kaynakta temizlendi ve `allow_nan=False` ile bir daha sessiz geçmez. Dosyadan açılmaz (`file://` modül yüklemeyi engeller) → `tools/view.py` yerel sunucu başlatır.
- Sınır: ayrıntılı klinker (tam LOD) 37 MB IFC'den gelir; GLB'de 15 panel tek mesh olduğu için yük hafif. Mahal hacimleri IFC'den (varsayılan kapalı).

## Düzeltme (2026-11-01): MCP başlatma hatası
`.mcp.json` ve README'deki `python -m brain.mcp_server` komutu `brain` modülünü bulamıyordu → Claude'da `CONNECTION_CLOSED`. Önceki smoke testim `PYTHONPATH` ekleyerek hatayı gizlemişti. Çözüm: `tools/mcp_server.py` başlatıcısı (src/ yolunu kendisi ekler); `tests/test_mcp_launch.py` artık `.mcp.json`'daki komutu olduğu gibi, başka çalışma klasöründen, `PYTHONPATH` olmadan başlatır. Revit kurulum bitince "RB 3D" görünümü artık otomatik öne gelir (`show_3d`; `status` aktif görünümü gösterir).

## P6 (2026-10-31): klinker cephe + merdiven kotu hatası — Revit'te doğrulandı; IFC/IDS/rapor sırada
- **Klinker cephe (T05–T07 ✔):** `src/brain/brick.py` yerleşimi (sıra, bağ, açıklık kesimi, uç kesimi) hesaplar; `Ops/Bricks.cs` her panel için TEK DirectShape mesh üretir (tuğla = duvar yüzünde 2 cm rölyef kutu; derz = duvarın açık harç rengi, `RB Derz Harci`). LOD `full` (tek tek tuğla: **41 882 tuğla, 209 410 yüzey, Revit'te saniyeler**) ve `courses` (2 492 şerit, ~17× hafif); varsayılan `full`. 15 panel (ön 6, arka 6, serbest yan 3). `verify_model` her panelin parça sayısını yerleşimle karşılaştırır. Ölçülen: tahminimin aksine tam LOD ağır değil.
- **Doğrulayıcı gerçek hata yakaladı (2. kez):** L1→L2 merdivenleri 3–9 m arasında duruyordu (olması gereken 3–6), çatıyı kesiyor, 3B'de çatıda iki çentik yapıyordu. Basamak sayısı/yüksekliği doğru olduğu için görünmemişti. Düzeltme + `verify` artık merdivenin z aralığını denetler (`z_min_m/z_max_m`).
- **Revit tuzağı (kanıtlanmış, `stair_probe` ile):** `StairsRun.TopElevation/BaseElevation` setter'ları taban seviyesi 0 değilse hata verir ("top less than extension below base", eşik tam seviye kotu); değerler göreli. **Çözüm: kolun kotunu `CreateStraightRun` konum çizgisinin z'si belirler** (çizgi `from.Elevation + h1` → run b=h1, t=h2). Sahanlık kotu göreli.
- Planlayıcı: yan serbest cepheler (`facade=side`) de klinker alır; panel op'u `normal` (dışa bakan) taşır ve kendi kapı/pencerelerine bağımlıdır. Op sayısı 490 → 493.
- Test: 140 yeşil (`test_brick` 14 yeni); sahte Revit lod'u op'tan okur. Revit uyarıları 28 → 15 (9 örtüşen ayırıcı çizgi, 4 eksenden sapma, 2 kısa eğri).
- **T01 BIM yönetmeliği ✔ (kısmen):** "Mimarlık ve Mühendislik Projelerinin Dijital Olarak Hazırlanması Hakkında Yönetmelik" (RG 05.08.2026-33331, yürürlük 1.9.2027, bu proje için zorunlu değil). Gövde metni okundu (IFC = TS EN ISO 16739-1, SI birim, mahal numarası M7(2), varlık adı M11, kademeli geçiş); **EK-5/EK-6 (zorunlu IFC sınıf/öznitelik) PDF'i 10 MB sınırını aştığı için okunamadı** → IDS "genel IFC4 profili", yönetmeliğe uygunluk iddiası YOK. Ayrıntı: `docs/03-domain/05-bim-yonetmeligi.md`.
- **T02/T03/T04 ✔:** `RevitBackend.export_ifc` (Revit'in kendi IFC4 dışa aktarımı, base quantities, proje/yapı adı), `brain/ifc_check.py` (IFC ↔ spec sayı + mahal alanı), `brain/ids_profile.py` + `data/rules/project.ids` (10 şart). Gerçek Revit IFC'si: **IDS 10/10, sayılar spec ile birebir** (204/102/88/68/4/4), mahal alanı 1294.8 m² (spec 1295.16), klinker 15 panel IfcBuildingElementProxy; boyut 37 MB (tam LOD) / 5 MB (courses). IDS'in başarısız olabildiği kanıtlı: spec'ten üretilen yedek IFC 7 şarttan KALIR (Pset yok), tek hatalı mahal adı 101/102 olarak yakalanır (`tests/test_ids.py`).
- **T07 LOD ✔ (ölçüldü):** tam LOD 41 882 tuğla / 209 410 yüzey Revit'te ~19 s'de tüm modelle kurulur; ağır beklenirdi, değil. Varsayılan `full`.
- **T08 rapor ✔:** `generate_report` → `out/project-report.html` (656 KB, tek dosya, Revit PNG'leri gömülü): parsel+imar (plana karşı TAKS/KAKS/Hmax), plan, Revit 3B+planlar, **spec↔Revit↔IFC tablo**, verify, IDS, senaryolar, sınırlar. Ölçülmeyen "—" yazar, 0 yazmaz.
- **Oda etiketleri ✔:** `tag_room` op'u (102 etiket, ad+numara+alan), `verify` sayar. Op sayısı 595.
- **Senaryolar:** `tools/scenarios.py` S-A, S-B, S-C, S-D, **S-F (klinker+IFC)** hepsi geçti; 154 pytest.
- **Kalan (P6):** parapet (planlayıcıda duvar olarak eklenmeli; şimdilik bilinen sınır), stretch S1 (tarayıcı IFC viewer), S2 (belge→ZoningParams). **Sonra P7:** README (dürüst sınırlar), mimari anlatım, video planı/çekim, temiz klon testi, teslim.

## P5 (2026-10-31, gece): MCP + test motoru — yazıldı, Revit'te büyük ölçüde doğrulandı
- `src/brain/mcp_server.py` (mcp 2.3, `MCPServer`, stdio): 10 araç — `list_inputs, load_parcel, check_zoning, plan_building, validate_spec, build_in_revit, verify_model, export_views, export_ifc, get_status`. Katman: `service.py` (Session; hatalar `{ok:false, error, hint}`), `verify.py`, `catalog.py`. `.mcp.json` ve README'de bağlama komutu. Gerçek stdio MCP istemcisiyle (`tools/mcp_smoke.py`) uçtan uca koştu: sıfır projede 490 eleman, **42 s**, `verify_model` 0 fark.
- **Doğrulayıcı gerçek hata yakaladı:** S-B (kat yüksekliği 2.90 m) sırasında 3 duvar Revit'te yoktu, oysa `apply` "created" demişti → kaynak: planlayıcı iki odanın 5–10 cm'lik köşe temasında bile duvar parçası üretiyordu, Revit bunları sessizce atıyor. Düzeltmeler: planlayıcı < 0.25 m parçaları üretmez (502 → 490 op, 216 → 204 duvar); `apply` sonunda yok olmuş eleman varsa `element_vanished` ile geri alır.
- **S-C kapısı:** doğrulama hatası olan plan `build_in_revit` ile Revit'e gönderilmez (`blocked`). "4 kat" → Z-KAT, Z-KAKS, Z-HMAX FAIL. Ön bahçe 2 m ise PAİY M23 varsayılanı plan notuyla aşılabildiği için kasıtlı olarak `warn` (FAIL değil).
- **Ölçüm ayrıntısı (dürüstlük):** duvarsız çekirdek odalarında (lobi/merdiven/arka hol) Revit oda ayırıcı çizgi uçlarını duvar yüzlerine oturtuyor → alan farkı ≤ %2.5 (0.25 m²). Bu odalar için tolerans %5, duvarlı odalar %2 (`verify.py`, gerekçe kodda).
- **Revit tuzakları (P5):** belge değiştirme (`new_project`) Idling olayında yasak → kuyruk artık bunu yalnız ExternalEvent'te çalıştırır (host değişikliği); açık dosyanın üzerine kaydetmek reddedilir → çakışmayan ad (`-2`) ve eski köprü projelerini kapatma.
- Senaryolar: `tools/scenarios.py` (S-A…S-D, `out/test-report.md`); S-B tek başına `tools/scenario_b.py`: **6/6 geçti** (2.90 m uygular, ikinci uygulama 0 değişiklik, 3.00'a döner).
- Testler: 123 yeşil (`test_verify`, `test_service`, `test_mcp_server`, sahte Revit `tests/fake_revit.py`).
- **Doğrulandı (2026-10-31 02:51):** `tools/scenarios.py` tam koşu — S-A (6/6), S-B (6/6), S-C (4/4), S-D (2/2) + 124 pytest, `out/test-report.md` yazıldı. Ana DLL kuyruk düzeltmesiyle sıfır projede kurulum artık deterministik (39–40 s). Projesiz Revit'te `dry_run` çevrimdışı derlemeye düşer.
- **Eksik:** S-E (belgeden veri, stretch), gerçek `claude mcp add` denemesi (kullanıcı makinesinde), Revit IFC + IDS (P6), klinker (P6), oda etiketleri/parapet/çatı çentiği (görsel cila).

## P4 (2026-10-31, Cumartesi gece): REVIT'TE ÇALIŞIYOR — gerçek parsel Revit'te kuruldu
`uv run python tools/build_in_revit.py [--new-project]` → 490 op uygulanır, model spec ile karşılaştırılır: **0 fark**.
- Kurulan: 4 seviye (+kat planı görünümleri), 216 duvar, 6 döşeme (merdiven boşluklu), 2 çatı, 102 oda, 88 kapı, 68 pencere, 4 U-merdiven.
- Doğrulananlar (Revit 2027.3'te ölçüldü): oda alanları ±%2; döşeme alanı; **merdiven 19 rıht, 0.1579 m, basamak 0.300 m = spec**; kapı/pencere sayıları; **idempotency** (ikinci uygulama: 490 unchanged); **gerçek rollback** (işlem ortasında hata → duvar sayısı 216 → 216).
- `out/revit-views/` altında Revit'in kendi PNG'leri (3B + kat planları) — `RevitBackend.export_views()`.
- **Sıcak yükleme:** yürütücüler `RevitBridge.Ops.dll`'de, host her çağrıda dosya değiştiyse yeniden yükler (Revit'i kapatmadan geliştirme). Host (`RevitBridge.dll`) yalnız protokol değişince; o zaman Revit yeniden başlatılır. `tools/install-addin.ps1` ikisini de kurar.
- **Düzeltilen yanlış bilgi:** "Revit 2027'de kapı/pencere ailesi yok" YANLIŞTI. DefaultMetric şablonu `M_Single-Flush` ve `M_Window-Casement-Double` ailelerini getiriyor; gerçek aile örnekleri duvara bağlı yerleştirilir (yedek yol DirectShape duruyor, kullanılmıyor).
- **Planlayıcı hatası düzeltildi:** pencere denizliği (0.9 m) op'a aktarılmıyordu.
- **Revit tuzakları:** (1) merdiven kol kotları MUTLAK kot; (2) kol çizgisi taban seviye düzleminde; (3) merdiven tipinin MaxRiser/MinTread'i spec'e göre ayarlanmazsa Revit kendi rıht sayısını seçer; (4) döşeme/çatı tipi için şablon tipinin kendi CompoundStructure'ı kullanılmalı (sıfırdan tek katman EndCap hatası); (5) açık çekirdek alanında oda ayırıcı çizgi gerekir; (6) yeniden kurarken "Can't keep elements joined" → varsayılan çözüm uygulanır ve uyarı olarak kaydedilir; (7) duvar uçları karşı duvar eksenine uzatılır (ölçüm farkı ≤ yarım kalınlık, hata değil).
- **Revit uyarıları (28, engelleyici değil):** 12 örtüşen duvar, 6 örtüşen ayırıcı çizgi, 4 "eksenden hafif sapma", 2+2 merdiven uç yüksekliği, 2 "eğri çok kısa" (planlayıcıdaki ~5 cm'lik duvar parçaları). Planlayıcıda bu kısa parçaların elenmesi iyileştirme adayı.
- **Açık/bilinen:** çatıda iki küçük beyaz çentik (3B görüntüde; nedeni incelenmedi); parapet yok (`parapet_h` kullanılmıyor); klinker panelleri (`create_brick_panel`) P6'da — şimdilik dış duvarın malzemesi klinker rengi; kapı/pencere aile boyutları spec'e göre çoğaltılmış tipler (çalışma-zamanında doğrulanmadı: yalnız sayı kontrol edildi).
- Sıradaki: P5 (MCP sunucusu + `verify_model`), P6 (IFC dışa aktarım, klinker, rapora Revit görüntüleri, üç yönlü metraj), alternatifler (W3).

## P3 (2026-10-31): REVIT'TE DOĞRULANDI
`bridge_smoke.py --new-project` Revit 2027.3'te geçti: ping, status, new_project, dry-run (model değişmedi), create_level ×2 (created 4 → unchanged 4), yükseklik değişince updated 1, bilinmeyen op reddi, read_back.
**Tuzak:** Revit 2027 `%LOCALAPPDATA%` altındaki DLL'yi reddetti (`WrongAssembly`, "does not exist"); DLL artık `%APPDATA%\Autodesk\Revit\Addins\2027\RevitBridge\` altında (install-addin.ps1 güncel). Güvenlik penceresi çıkmadı.
**Doğrulanmayan:** işlem ortasında gerçek rollback (smoke testteki kötü op ön doğrulamada reddedildi, transaction'a girmedi). **Açık iş:** şablonun varsayılan "Level 1/Level 2" seviyeleri duruyor; P4'te yeniden kullan/sil.

(Eski not) P3: kod yazıldı, derlendi, kuruldu
87 Python testi yeşil (7'si Revit istemci protokolü, sahte sunucuyla). Add-in `%LOCALAPPDATA%\RevitBridge\bin\` altına ve manifest `%APPDATA%\Autodesk\Revit\Addins\2027\RevitBridge.addin` olarak kuruldu. Revit (pid 8928, 2027.3 TRIAL) **açıktı**, eklentiyi yalnız yeniden başlatınca yükler.
**Kullanıcıdan:** Revit'i kapatıp yeniden aç → güvenlik penceresinde **"Always Load"** seç → bana haber ver. Sonra `uv run python tools/bridge_smoke.py --new-project` ile doğrulanır (ping, status, new_project, create_level ×2 idempotency, rollback, dry-run).
**Revit'te çalıştırılana kadar "çalışıyor" denmez.**

## DURUM (2026-10-31): Planlayıcı v2 bitti — 80 test yeşil
Gerçek parsel (Karatay/Büyüksinan 1495/26) için uçtan uca çalışıyor: `uv run python tools/plan_demo.py` → `out/{spec,ops}.json, model.ifc, report.html`; kat planı `tools/plan_view.py`.
- `neighbors.py` + `data/parcels/*.neighbors.json`: kenar rolleri TKGM komşu kanıtından (yol: 5, 9, 10 — kullanıcı teyitli).
- `planner.py` v2: eksen çerçevesi, yol ucu başına blok, TAKS'tan derinlik, Madde 24(2) 6 m kuralı, oda dikdörtgenlerinden duvar çıkarımı.
- Sonuç: 2 blok (18.75×13.25 ve 18.0×13.25), TAKS 0.399, KAKS 1.197, 102 mahal, 216 duvar, 502 op; `validate_spec` hatasız/uyarısız; party boşluğu ≤ 0.29 m.
- IFC yedek yolu, altın dosyalar (`tests/golden/*_karatay_1495_26.json`), rapor (vaziyet planı dahil) güncel.
- Tasarım: `docs/03-domain/04-kat-plani-tasarimi.md`.
**Sıradaki:** P3 (Revit köprüsü) — Revit 2027 kurulu, hedef `net10.0-windows`. Sonra P4 yürütücüler, readback, klinker cephe, MCP, alternatifler (W3), metraj (W4), Revit görüntüsü (W8). **Revit'te hâlâ hiçbir kod çalıştırılmadı.**
Takvim: Cumartesi P3+ilk Revit modeli · Pazar P4+readback+cephe+MCP (22:00 kod donar) · Pazartesi teslim.

## PLAN v2 (2026-10-30) — oku: `docs/00-genel/05-plan-v2.md`
Teslim **Pazartesi 2026-11-02**. TKGM komşu sorgusuyla kenar rolleri veriden çıkarıldı: **kenarlar 0–4 ve 6–8 komşu parsel (party), 9–10 kamu alanı/yol (≈3–6 m, kullanıcı teyitli), 5 kamu alanı ≥ 15 m (yol/park? teyit bekliyor).** Konya Büyükşehir İmar Yönetmeliği (RG 17.04.2026-33227) bulundu; yol genişliğine bağlı kat adedi tablosu var. Parselin imar durumu (TAKS/KAKS/kat adedi) hâlâ bilinmiyor → kullanıcıdan istendi. Planlayıcı v2 gerekli (çok kenarlı cephe, dışbükey olmayan alan, derin plan).
**Kullanıcı yanıtı (2026-10-30):** kenar 5'te de yol var → parsel iki ucundan yola, iki uzun kenarından komşuya açık. Kullanıcı imar durumunu elle aramak istemiyor; girdi/çıktı tanımı `docs/02-mimari/04-girdi-cikti.md`'de netleştirildi (otomatik: parsel+komşu+yol+kurallar; elle: yalnız imar durumu belgesi veya varsayım).
**Kullanıcı kararı bekleyen:** plan v2 onayı, kenar 5 nedir, imar durumu belgesi, hangi "etkileyici" özellikler (W3 W4 W8 önerildi).

## Gerçek parsel alındı (2026-10-30)
Kullanıcı parseli verdi: **Konya / Karatay / Büyüksinan (mahalleId 127989), ada 1495, parsel 26**, tapu 1.220,51 m², nitelik "Betonarme İki Adet Beş Katlı Apartman ve Arsası" (kat mülkiyetli, **üzerinde mevcut iki bina var**), pafta 20M 4. TKGM API'den çekilip `data/parcels/karatay-buyuksinan-1495-26.geojson` olarak donduruldu (11 köşe, 5 ondalık derece ≈ 1 m hassasiyet). Doğrulama: hesaplanan alan 1223,42 m² (fark %0,24), EPSG:5255. `tools/parcel_view.py` numaralı kenar çizimini üretir.
Geometri: ~70 × 17 m çapraz şerit, **dışbükey değil** (kenarlar 0–10). Kenar rolleri henüz yok (kullanıcıdan bekleniyor: yol cephesi hangisi?). Planlayıcı şu an dışbükey alan + dar (≤ ~20 m) cephe varsayıyor; uzun cephede genişlik sınırı ve dışbükey olmayan alan desteği gerekecek.

## Şu an
**P2 kod olarak bitti: 69 test yeşil.** Revit gerektirmeyen çekirdek (parsel → imar → plan → doğrulama → op listesi → IFC) uçtan uca çalışıyor. Sıradaki: P3 (Revit add-in çekirdeği) — **Revit kurulumu ve sürümü beklenen tek bağımlılık.**

## Faz durumu
| Faz | Durum | Not |
|---|---|---|
| P0 Ortam/iskelet | ▶ | T02 (Revit edinimi) ve T09 (sürüm kaydı) kullanıcıda |
| P1 Şema/parsel/imar | ▶ | T01: gerçek parsel bulunamadı → sentetik parsel |
| P2 Planlayıcı/derleyici | ☑ | T01–T10 bitti (aşağıda) |
| P3 Add-in çekirdek | ☐ | Revit gerekir (derleme gerekmez) |
| P4 Op yürütücüler | ☐ | |
| P5 MCP + test motoru | ☐ | MCP sunucusu Revit'siz de başlayabilir |
| P6 IFC/cephe/rapor | ☐ | |
| P7 Doküman/video/teslim | ☐ | |

## P2 sonucu
| ID | Sonuç |
|---|---|
| T01 | `planner.largest_rect`: dışbükey yapılaşma alanında en büyük dikdörtgen, TAKS tavanı, 5 cm modül. 14×30 parselde ayak izi 14×12 m (168 m²) |
| T02–T03 | 3 kat + çatı düzeyi; iki kollu merdiven PAİY M31'e göre hesaplanıyor (19 rıht, 0.158 m, basamak 0.30, 2a+b = 61.6 cm) |
| T04–T06 | Çekirdek şeridi, daire A/B (ayna), 39 mahal, 42 duvar, kapı/pencere; bitişik duvarda açıklık yok |
| T07 | `validate.py`: id/referans bütünlüğü, açıklık-duvar yerleşimi, mahal çakışması, düşey hizalama, erişim grafı (BFS), PAİY M29/M30/M31/M28, imar kontrolleri |
| T08 | `compiler.py`: 151 op, topolojik sıra, deterministik |
| T09 | `tests/golden/` spec ve ops altın dosyaları (`UPDATE_GOLDEN=1` ile yenilenir) |
| T10 | `backends/ifc.py`: IFC4; duvar/döşeme/oda/merdiven/çatı/kapı-pencere + void-fill + Qto; geometri testle doğrulandı |
Çıktı üretimi: `uv run python tools/plan_demo.py` → `out/spec.json, ops.json, model.ifc, report.html`; kat planı: `uv run python tools/plan_view.py L1`.
Testte yakalanan gerçek hatalar: yinelenen kapı/pencere id'si (`S-DUP-ID`), IFC birimleri (mm yerine m).

## Bilinen sınırlar (README'de de yazılacak)
- **Parsel sentetik** (14×30 m); imar parametreleri **demo varsayımı** (TAKS/KAKS/Hmax).
- Planlayıcı yalnız dışbükey yapılaşma alanı ve ön kenara paralel dikdörtgen ayak izi.
- Merdiven çatıya ulaşmıyor (M31(1)(b)); yangın kaçış genişliği ve aydınlatma oranı kontrol edilmedi.
- IFC: yedek yol; stair/oda basitleştirilmiş hacim. Revit IFC'si P6.
- **Revit'te hiçbir kod henüz çalıştırılmadı.**

## Açık sorular / kullanıcıdan beklenenler
1. **Revit:** Edinim, kart, kurulum, sürüm (P3 için kritik; K1 kapısı Perşembe 12:00).
2. Gerçek parsel (mahalle/ada/parsel) — TKGM'de 20677/13 bulunamadı; yoksa sentetikle devam.
3. Gerçek imar durumu (TAKS/KAKS/Hmax/çekmeler) var mı?
4. Teslim Cuma saat kaçta, yazılı görev tanımı?
5. P3'e geçiş onayı.

## TKGM parsel bulguları
API çalışıyor (Konya=64, Karatay=651, Sariyakup=128029); `parsel/128029/20677/13` → 404. Ayrıntı: bu dosyanın önceki sürümü ve `docs/03-domain/01-parsel-ve-koordinat.md`.

## Doğrulanamayanlar
Revit deneme kartı/sürümleri · Konya/Karatay plan notları ve parsel TAKS/KAKS/Hmax · "yeni BIM yönetmeliği" gereksinimleri (P6-T01) · Visual Studio iş yükleri (gerekmiyor).

## Bilinen küçük konular
- Mutlak yol kullan; Bash'te `uv` PATH'te yok → PowerShell (`$env:Path` yenile).
- Commit atılmadı (kullanıcı isterse).

## Sonraki adım
Revit kuruluysa P3 (RPC, ExternalEvent, transaction, spec_id); değilse P5'in MCP sunucusu ve P6-T05 (tuğla üreteci) Revit'siz ilerleyebilir.
