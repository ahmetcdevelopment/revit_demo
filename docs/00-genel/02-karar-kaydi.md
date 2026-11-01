# 02 · Karar Kaydı (ADR)

Her karar: **Karar · Gerekçe · Alternatif · Durum**. Değişirse yeni satır eklenir, eskisi silinmez (Superseded işaretlenir).

| ID | Karar | Gerekçe | Alternatif | Durum |
|---|---|---|---|---|
| D01 | Revit **ana** hedef; maliyet 0 | Kullanıcı kararı; deneme/Education lisansı ücretsiz | Sadece IFC | Aktif |
| D02 | Mimari: Python "Beyin" + C# ince Revit add-in | Zekâ Revit'siz test edilir; Revit API tek thread'li, add-in ince kalmalı | Her şeyi C#'ta | Aktif |
| D03 | Claude ↔ Beyin: **MCP (stdio)** | Claude Desktop/Code aboneliğiyle API ücreti yok | Anthropic API | Aktif |
| D04 | Beyin ↔ Add-in: **localhost JSON-RPC (HTTP veya named pipe) + token** | Basit, test edilebilir | gRPC, WebSocket | Aktif (taşıma P3'te netleşir) |
| D05 | LLM'in çıktısı **BuildingSpec (JSON)**; geometriyi **deterministik derleyici** üretir | Tekrarlanabilirlik, test, idempotency | LLM'e düşük seviye araç vermek | Aktif |
| D06 | Elemanlara **ExtensibleStorage** ile `spec_id` yazılır | Reconcile/diff, idempotent güncelleme | Parametre/isim ile eşleme | Aktif |
| D07 | Hedef **Revit 2027 / .NET 10** (kurulacak sürüm 2027 ise) | 2026-10 itibarıyla güncel deneme sürümü; kullanıcının makinesinde .NET 10 SDK var | 2025/2026 (.NET 8) | Aktif, P0'da doğrulanır |
| D08 | Add-in, Revit kurulu olmadan da **NuGet API paketleriyle derlenir** (Nice3point.Revit.Api.*) | Kurulum beklerken derleme doğrulanır | Revit DLL'leri bekle | Aktif |
| D09 | Python: **uv** ile yönetilen Python 3.12 | Bu makinede Python yok (yalnızca Store stub'ı); uv ücretsiz, tek komut | python.org kurucu | Aktif, kullanıcı onayı P0'da |
| D10 | IFC: IfcOpenShell + ifctester (IDS) | Ücretsiz, standart | — | Aktif |
| D11 | Klinker cephe: panel başına **tek DirectShape/tessellated mesh** | Binlerce ayrı eleman Revit'i kilitler | Her tuğla ayrı eleman | Aktif |
| D12 | Parsel: TKGM verisi **fixture JSON olarak dondurulur**; canlı API opsiyonel yardımcı | API belgelenmemiş, değişebilir/engellenebilir; demo deterministik olmalı | Canlı çağrıya bağımlı demo | Aktif |
| D13 | İmar kuralları **YAML + madde atfı + verified bayrağı** | Denetlenebilirlik, dürüstlük kuralı | Koda gömülü sabitler | Aktif |
| D14 | Fallback: Revit sorun çıkarırsa `IfcBackend` ile aynı Spec'ten IFC | Revit riskine karşı sigorta | — | Yedek, P4 sonunda karar |
| D15 | Dil: dokümanlar Türkçe, kod/identifier İngilizce | İşveren Türk; kod uluslararası okunur | — | Aktif |
| D16 | Teslim Pazartesi 2026-11-02; Pazar 22:00 kod donar | Kullanıcı bildirimi (2026-10-30) | Cuma teslim | Aktif |
| D17 | Gerçek parsel: Karatay / Büyüksinan, ada 1495 parsel 26 (sentetikler yalnız regresyon fixture'ı) | Kullanıcı sağladı; TKGM'den doğrulandı | Sentetik demo | Aktif |
| D18 | Kenar rolleri TKGM koordinat sorgusuyla **veriden** çıkarılır, kullanıcı teyit eder | Tahmin yerine kanıt | Elle atama | Aktif |
| D19 | Kalite çıtası: çift hesap, üç yönlü eşitlik (spec↔Revit↔IFC), kaynak zinciri, negatif testler | Mimarlık şirketi hedef kitlesi | — | Aktif |
| D20 | Konya Büyükşehir İmar Yönetmeliği ayrı kural kataloğu olarak PAİY'in yanına eklenir | Yerel yönetmelik (RG 17.04.2026-33227) PAİY'e ek hükümler getiriyor | Yalnız PAİY | Aktif, metin okuması bekliyor |
| D21 | Planlayıcı v2: çok kenarlı cephe, dışbükey olmayan alan, derin plan tipolojisi, alternatif üretimi | Gerçek parsel 70×17 m şerit | Tek çekirdekli dar plan | Aktif |
