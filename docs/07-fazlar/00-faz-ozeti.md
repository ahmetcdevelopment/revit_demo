# 00 · Faz Özeti ve Takvim

Teslim: **Cuma 2026-10-30** (saat bilinmiyor → varsayım: gün sonu; hedef: Perşembe gece her şey bitmiş, Cuma yalnız çekim/cila).
Bugün: Çarşamba 2026-10-28.

| Faz | Ad | Revit gerekir mi | Zaman kutusu | Çıktı |
|---|---|---|---|---|
| **P0** | Ortam, lisans, repo iskeleti | — | Çar akşam (≈1 sa aktif + arka plan indirme) | Python, git, Revit kurulumu başladı |
| **P1** | Şemalar, parsel, imar motoru | Hayır | Çar akşam–Per sabah | `parcel` + `zoning` + testler yeşil |
| **P2** | Planlayıcı, derleyici, offline testler | Hayır | Per sabah | BuildingSpec + Op listesi, altın dosyalar |
| **P3** | Revit add-in çekirdeği + köprü | Evet (derleme: hayır) | Per öğlen | RPC + ExternalEvent + transaction + spec_id |
| **P4** | Op yürütücüler: Level→Wall→Floor→Stair→Room→Door/Window→Roof | Evet | Per öğleden sonra | Revit'te bina |
| **P5** | MCP sunucusu + readback test motoru + idempotency | Evet | Per akşam | Claude'dan uçtan uca |
| **P6** | IFC/IDS, klinker cephe, rapor (viewer = stretch) | Kısmen | Per gece | IFC + cephe + rapor |
| **P7** | README, diyagram, video, teslim paketi | Evet | Cuma | Teslim |

## Bağımlılık grafı
```
P0 ─┬─► P1 ─► P2 ─┬─► P3 ─► P4 ─► P5 ─► P6 ─► P7
    │            └──────────► (IfcBackend yedek)
    └─ Revit kurulumu (arka plan) ───────────► P3/P4 doğrulaması
```

## Kapılar
- **K1 (Per 12:00):** P1+P2 bitti ve Revit çalışır durumda mı? Hayır → D14 (IfcBackend yedeğine geç), Revit iddiası kaldırılır/etiketlenir.
- **K2 (Per 20:00):** Revit'te kütle+duvar+döşeme+oda var mı? Hayır → merdiven/kapı/pencere sadeleşir (kesme çizgisi).
- **K3 (Cuma 10:00):** Çekim başlar; sonrası yalnız hata düzeltme.

## Görev kimliği
`P<faz>-T<no>` · Durum: ☐ bekliyor · ▶ sürüyor · ☑ bitti · ✖ kesildi · Her görev: Girdi / Çıktı / Kabul. Durum güncellemeleri `PROGRESS.md`'de.

## Sahiplik
Ajan = kod/doküman · Kullanıcı = hesap açma, indirme, onay, Revit'te görsel kontrol, çekim.
