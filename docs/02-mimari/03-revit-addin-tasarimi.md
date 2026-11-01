# 03 · Revit Add-in Tasarımı

## Proje yapısı (`src/revit-addin/`)
```
RevitBridge.sln
├─ RevitBridge/                    # Revit'e yüklenen derleme
│   ├─ App.cs                      # IExternalApplication: startup, RPC sunucusu, ribbon (opsiyonel)
│   ├─ Rpc/RpcServer.cs            # HttpListener 127.0.0.1:<port> + token kontrolü
│   ├─ Rpc/Dtos.cs                 # Op, ApplyResult, VerifyReport (System.Text.Json)
│   ├─ Threading/CommandQueue.cs   # kuyruk + ExternalEvent + TaskCompletionSource
│   ├─ Threading/ApplyHandler.cs   # IExternalEventHandler: ana thread'de çalışır
│   ├─ Ops/*.cs                    # Level, Wall, Floor, Roof, Stair, Room, Door, Window, BrickPanel
│   ├─ Reconcile/SpecIdStore.cs    # ExtensibleStorage şeması (spec_id)
│   ├─ Reconcile/Differ.cs         # modeldeki spec_id'ler ↔ gelen op'lar
│   ├─ Verify/Readback.cs          # eleman sayıları, alanlar, parametreler, uyarılar
│   ├─ Ifc/IfcExporter.cs          # Document.Export(IFCExportOptions)
│   └─ RevitBridge.addin           # manifest (kullanıcı bazlı konuma kopyalanır)
└─ RevitBridge.Tests/              # Revit'siz birim testleri (DTO, sıralama, matematik)
```

## Kritik mekanizmalar
1. **Ana thread:** Revit API'si yalnız Revit thread'inde güvenli. RPC isteği → `CommandQueue.Enqueue(job)` → `ExternalEvent.Raise()` → handler `Execute(UIApplication)` içinde işler → `TaskCompletionSource.SetResult`. `ExternalEvent.Raise()` Revit boştayken tetiklenir; boşta `Idling` olayı ile tetiklemeyi güvence altına alma gerekebilir (P3'te test edilir).
2. **Transaction:** `TransactionGroup` (apply) > `Transaction` (op grubu). Hata → `Assimilate` yerine `RollBack`. `FailuresPreprocessor` uyarıları toplar/siler.
3. **spec_id kalıcılığı:** `Autodesk.Revit.DB.ExtensibleStorage.Schema` (GUID sabit) → `Entity` her eleman üzerinde `spec_id` + `op_hash`. Reconcile: aynı `spec_id` + aynı `op_hash` → atla; farklıysa güncelle; modelde olup spec'te olmayan → sil.
4. **Birimler:** Revit içi **feet**; tüm giriş metre → `UnitUtils.ConvertToInternalUnits(v, UnitTypeId.Meters)`.
5. **Aile (family) bağımlılığı:** Kapı/pencere için şablonla gelen aileler kullanılır (`FamilySymbol` adı eşlemesi). Aile bulunamazsa net hata + fallback tablosu. Şablon: Revit "Architectural Template"; tür adları sürüme göre değişebilir → `ops` içinde `family_hint` + ad eşleme tablosu (`data/rules/revit-family-map.yaml`).
6. **Tuğla paneli:** `TessellatedShapeBuilder` + `DirectShape.CreateElement(doc, BuiltInCategory.OST_GenericModel…)`. Tuğla ve derz ayrı malzeme/ID (iki DirectShape veya iki face set). Panel = bir cephe parçası (kat × cephe).
7. **Oda (Room):** Duvarlar kapalı döngü oluşturmalı; `doc.Create.NewRoom(level, UV)`; ardından `Room.Area` readback. Oda ayırıcılar (room separation lines) gerekirse eklenir.
8. **Merdiven:** `StairsEditScope` ile `StairsRun.CreateStraightRun`/`CreateSketchedRun`. Başlangıç: iki kollu, sahanlıklı; başarısızlık riskli → R08 kesme çizgisi.
9. **IFC:** `IFCExportOptions { FileVersion = IFC4, ... }`; ayrıntılar P6'da.

## Yükleme (kullanıcı bazlı)
Manifest: `%AppData%\Autodesk\Revit\Addins\<sürüm>\RevitBridge.addin`, `Assembly` yolu `bin` çıktısına işaret eder. (Revit 2027'de All-Users konumu `Program Files`'a taşındı; kullanıcı bazlı konum desteklenmeye devam ediyor.)

## Derleme
`dotnet build -c Release` · `global.json` ile SDK sabitlenir · NuGet: `Nice3point.Revit.Api.RevitAPI`, `Nice3point.Revit.Api.RevitAPIUI` (sürüm = hedef Revit sürümü) · Hedef framework Revit sürümüne göre (`net10.0-windows` / `net8.0-windows`).

## P3 sonrası gerçek durum (2026-10-31)
- Çözüm dosyası `RevitBridge.slnx` (.NET 10 varsayılanı); proje `net10.0-windows`, Revit API paketleri `ExcludeAssets="runtime"` (Revit kendi DLL'lerini sağlar).
- Yazıldı ve **derlendi**: `App` (başlatma, Idling + ExternalEvent kuyruğu, `endpoint.json` yazımı), `RpcServer` (127.0.0.1, rastgele port, `X-Bridge-Token`), `RpcDispatcher` (`ping`, `status`, `new_project`, `apply_ops`, `read_back`), `CommandQueue` (TaskCompletionSource, zaman aşımında işi iptal eder), `OpRunner` (TransactionGroup, `dry_run` = geri al, hata = tümü geri alınır, op doğrulaması önce), `BridgeFailures` (uyarıları toplar+siler, hata = rollback), `SpecIdStore` (ExtensibleStorage, `SpecRef/OpHash/SpecId`), `Metric` (m↔ft), `BridgeLog` (log.txt + replay.jsonl).
- Şimdilik yalnız **`create_level`** (idempotent: created/updated/unchanged). Diğer op'lar `unsupported_op` döner (P4).
- **Düzeltme (P4):** `Libraries\English` klasöründe kapı/pencere yok, ama `DefaultMetric.rte` şablonu kendi aileleriyle gelir (`M_Single-Flush`, `M_Window-Casement-Double`, `M_Fixed`). P4 bunları duvara bağlı yerleştirir; boyut için `RB Door 900x2100` gibi çoğaltılmış tipler. Aile yoksa yedek: `NewOpening` boşluğu + DirectShape (kapı/pencere kategorisi).
- **İki derlemeli yapı (P4):** `RevitBridge.dll` (host: App, RPC, kuyruk, günlük, `OpsLoader`) ve `RevitBridge.Ops.dll` (yürütücüler, ProjectOps, ViewExport). Host, Ops'u baytlardan toplanabilir bir `AssemblyLoadContext`'e yükler ve dosya değişince yeniden yükler → Revit açıkken derle-dene döngüsü. Ping `ops_version` döner. Host `ping` dışında her yöntemi `Entry.Handle` ile Ops'a yollar (yeni yöntem eklemek host değişikliği gerektirmez).
- Op özeti `OpRunner.Revision` içerir: yürütücü çıktısı değişince Revision artırılır, eski eleman yeniden kurulur. `prune: true` spec'te olmayan etiketli elemanları siler.
- Şablon: `C:\ProgramData\Autodesk\RVT 2027\Templates\English\DefaultMetric.rte`.
- Kurulum: `tools\install-addin.ps1` (kullanıcı bazlı: `%LOCALAPPDATA%\RevitBridge\bin` + `%APPDATA%\Autodesk\Revit\Addins\2027\RevitBridge.addin`). Duman testi: `tools\bridge_smoke.py`.
- **Revit içinde henüz çalıştırılmadı.** Python istemci protokolü sahte sunucuyla test edildi (7 test).

## Yapılmayanlar (bilinçli)
UI paneli, WPF, bulut modeller, Dynamo bağımlılığı, çoklu doküman.
