# P4 · Op Yürütücüler (Revit'te Bina)

**Amaç:** Op listesini Revit'te gerçek elemanlara çevirmek.

| ID | Görev | Kabul |
|---|---|---|
| P4-T01 | `create_level` (kat kotları) | Seviye sayısı/kot readback |
| P4-T02 | `create_wall` (tipler: dış, party, dahili, çekirdek; kalınlık; kat bağlantısı); duvar tipi oluşturma/seçme | Sayı/uzunluk eşleşiyor |
| P4-T03 | `create_floor` (+ merdiven açıklığı) | Alan = poligon alanı |
| P4-T04 | `create_stair` (iki kollu; yedek: düz) | Basamak sayısı/rıht readback |
| P4-T05 | `create_room` (UV nokta, adlandırma) | Oda alanı ±%2 |
| P4-T06 | `place_door` / `place_window` (aile eşleme tablosu `revit-family-map.yaml`) | Host ilişkisi doğru |
| P4-T07 | `create_roof` (düz/teras) | Çatı elemanı var |
| P4-T08 | Differ + idempotent uygulama (spec_id/op_hash) | İkinci `apply` = 0 değişiklik |
| P4-T09 | `Readback` (sayılar, alanlar, uyarılar, yetimler) | JSON raporu |
| P4-T10 | Karatay Spec'i ile tam bina; görsel kontrol (3B, plan) | Kullanıcı ekran görüntüsüyle onaylar |

**Durum (2026-10-31):** T01–T09 Revit'te çalışıyor ve ölçüldü (spec karşılaştırması 0 fark, idempotency, rollback). T10: 3B + kat planı PNG'leri `out/revit-views/` altında; kullanıcı onayı bekleniyor. Ayrıntı: `PROGRESS.md`.

**DoD:** Karatay binası Revit'te üretiliyor; readback yeşil; idempotency sağlanıyor. **Kapı:** K2.
**Kesme çizgisi:** Merdiven/kapı/pencere zorlaşırsa sadeleştir (R08); kütle+duvar+döşeme+oda şarttır.
