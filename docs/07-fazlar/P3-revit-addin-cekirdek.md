# P3 · Revit Add-in Çekirdeği ve Köprü

**Amaç:** Beyin ↔ Revit güvenli, tek-thread'li, atomik iletişim.

| ID | Görev | Kabul |
|---|---|---|
| P3-T01 | TargetFramework'ü Revit sürümüne göre sabitle; `.addin` manifesti; kullanıcı bazlı konuma kopyalayan `tools/install-addin.ps1` | Revit açılışında add-in yükleniyor (log satırı) |
| P3-T02 | `RpcServer` (127.0.0.1, token), `status` yöntemi | `curl` ile token'lı `status` cevabı |
| P3-T03 | `CommandQueue` + `ExternalEvent` + `TaskCompletionSource`; zaman aşımı | Ana thread'de çalıştığı log ile doğrulanır |
| P3-T04 | Birim dönüşümü ve yardımcılar (m↔ft) | Birim testleri (Revit'siz) |
| P3-T05 | `TransactionGroup` sarmalayıcı + `FailuresPreprocessor` (uyarı toplama) | Bilerek hata → rollback |
| P3-T06 | `SpecIdStore` (ExtensibleStorage) | Yaz/oku gidiş-dönüş; belgeyi kaydet-yeniden aç sonrası kalıcı |
| P3-T07 | `replay.jsonl` günlüğü | Her çağrı kayıtlı |
| P3-T08 | Python `RevitBackend` istemcisi (RPC) | `get_status` Python'dan çalışır |

**DoD:** Python'dan Revit'e `status` ve dummy bir `create_level` komutu gidip dönüyor; hata durumunda rollback ve net hata var.
**Riskler:** R01, R03, R04. **Kapı:** K1.
