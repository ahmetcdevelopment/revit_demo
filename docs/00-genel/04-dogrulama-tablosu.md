# 04 · Neyi test ettim, neyi varsaydım

## Doğrulandı (çalıştırıldı, sonucu görüldü)
| Konu | Nasıl | Sonuç |
|---|---|---|
| Spec → op → Revit | `build_in_revit` Revit 2027.3'te, `verify_model` | 0 fark (duvar 204, mahal 102, kapı 88, pencere 68, merdiven 4, klinker 15 panel) |
| Idempotency | aynı spec ikinci kez uygulandı | 0 değişiklik |
| Değişiklik (S-B) | kat yüksekliği değişti | yalnız etkilenen elemanlar güncellendi |
| Rollback (S-D) | bozuk op | model değişmedi, hata op id ile döndü |
| İmar ihlali (S-C) | 4 kat, dar çekme | imar motoru FAIL; `build_in_revit` `blocked`, Revit'e gitmedi |
| Merdiven | 19 rıht, 0.1579 m, basamak 0.30; kotlar Revit'ten okundu | spec ile uyumlu (PAİY M31) |
| Revit IFC4 | IDS (10 spec), sayı tutarlılığı, mahal alanı | 10/10; sayılar tutuyor; 1294.8 m² (spec 1295.16) |
| Tarayıcı görüntüleyici | gerçek tarayıcıda yüklendi, tıklama/kesit denendi | çalışıyor |
| MCP | gerçek başlatma komutuyla süreç açıldı | araçlar listelendi |
| Python testleri | `pytest` | 159 geçiyor (sahte Revit) |

## Varsayıldı / doğrulanmadı
| Konu | Neden |
|---|---|
| TAKS 0.40, KAKS 1.20, Hmax 10.5, kat 3, çekmeler 5/3/0/3 | Parselin imar durumu belgesi yok → demo varsayımı (`verified:false`) |
| Planlı Alanlar İmar Yönetmeliği (PAİY) maddeleri | Metinden okundu; Konya'ya özgü ek hükümler eklenmedi |
| BIM yönetmeliğine uygunluk | EK-5/EK-6 okunamadı; IDS genel IFC4 profili, uygunluk iddiası yok |
| Parsel koordinatları | TKGM, ±1 m |
| Revit lisansı | 2027.3 trial / ticari olmayan |
| Mevcut 5 katlı iki bina | Modellenmedi |

## Bilinen eksikler
Parapet, belgeden imar çıkarma (S-E), 15 Revit uyarısı (9 üst üste ayırıcı çizgi, 4 eksen dışı, 2 kısa eğri; engelleyici değil), MEP/yapısal.
