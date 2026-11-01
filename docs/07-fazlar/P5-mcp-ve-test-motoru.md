# P5 · MCP Sunucusu ve Test Motoru

**Amaç:** Claude'dan tek komutla uçtan uca akış ve kanıtlanabilir doğrulama.

| ID | Görev | Kabul |
|---|---|---|
| P5-T01 | MCP sunucusu (stdio): araç yüzeyi (`load_parcel … get_status`), kısa ve net açıklamalar | Claude Desktop/Code'a bağlanıyor, araçlar listeleniyor |
| P5-T02 | Claude bağlantı yapılandırması (`claude mcp add` veya Desktop config) ve belgesi | Kurulum adımları README'de |
| P5-T03 | `build_in_revit` modları (`dry_run` / `apply`) ve diff çıktısı | Dry-run Revit'siz de çalışır |
| P5-T04 | `verify_model`: spec↔readback karşılaştırma, rapor | Eşleşmezse net fark listesi |
| P5-T05 | Senaryo betikleri: S-A…S-D otomatik koşan `tools/scenario_*.py` | Her biri geçti/kaldı çıktısı |
| P5-T06 | Hata mesajı kalitesi (LLM'in anlayacağı), yeniden deneme politikaları | Bilerek hata testleri |
| P5-T07 | `out/test-report.md` birleşik rapor | Üç katman özetleniyor |

**DoD:** Claude'a verilen tek prompt ile S-A uçtan uca çalışıyor; S-B/S-C/S-D senaryoları gösterilebilir.
