# 02 · Video Senaryosu (≤ 5 dk) — konuşma metni ve çekim sırası

Kare planı: [01-demo-senaryolari.md](01-demo-senaryolari.md). Bu dosya söylenecek metin ve ekran sırasıdır. Gerçek süre prova ile ölçülür (hedef 4:45).

## Çekim öncesi
- Revit 2027 açık, add-in yüklü (`tools/install-addin.ps1`), boş şablon; `out/` temiz değil sorun değil, `scenarios.py` yeniden üretir.
- Claude Code/Desktop'ta `revit-demo` MCP bağlı (araç listesi görünüyor).
- Tarayıcıda `uv run python tools/view.py --build` hazır (model önceden üretilmiş olsun; üretim ~25 sn).
- Ekranda: Claude (sol), Revit (sağ). Ses: net, yavaş.

## Metin
**0:00 — Problem (ekran: repo klasörleri)**
"Bir parselden başlayıp imar kurallarını denetleyen ve Revit'te 3 katlı bitişik nizam apartman kuran bir sistem yaptım. Fikir şu: Claude niyeti tarif ediyor, geometriyi ise deterministik bir derleyici kuruyor. Yani model rastgele duvar çizmiyor; aynı girdi her seferinde aynı modeli veriyor."

**0:25 — Mimari (ekran: README'deki diyagram)**
"Claude, MCP ile Python beynine bağlanıyor. Beyin parseli okur, imarı madde atıflı denetler, bir BuildingSpec üretir, derleyici bunu sıralı işlem listesine çevirir. Revit'te küçük bir C# eklentisi bunu tek transaction grubunda uygular; hata olursa hepsi geri alınır."

**1:15 — Altın yol (ekran: Claude sohbeti)**
Komut: "Büyüksinan 1495 ada 26 parseli yükle, imar kontrolü yap, 3 katlı bitişik nizam apartman planla."
"Parsel TKGM'den geldi. İmar değerleri demo varsayımı; ekranda açıkça öyle etiketli, çünkü gerçek imar durumu belgesi elimde yok. Yapılaşma alanı, TAKS 0.399, KAKS 1.197."

**2:15 — Revit'te uygulama (ekran: Revit)**
"Önce dry-run: 595 işlem. Şimdi uygula." (zaman atlamalı) "Şimdi verify_model: modeli Revit'ten geri okuyup spec'le karşılaştırıyor — sıfır fark."

**3:15 — İdempotency ve ihlal**
"Kat yüksekliğini 2,90 yapıyorum: yalnız etkilenen elemanlar güncellendi. Aynı komut tekrar: sıfır değişiklik." 
"Şimdi 4 kat istiyorum: imar motoru KAT, KAKS ve HMAX'tan reddediyor, Revit'e hiçbir şey gitmiyor."

**3:45 — Cephe, IFC, 3B**
"Klinker cephe tuğla tuğla: 41 882 tuğla, derzli. IFC'yi Revit'in kendi dışa aktarıcısıyla aldım; proje IDS'ine karşı 10 şartın 10'u geçti, sayılar ve mahal alanı spec'le tutuyor." (tarayıcı görüntüleyiciyi aç, döndür, kesit, bir cepheye tıkla)

**4:30 — Sınırlar**
"Dürüst olayım: imar değerleri demo varsayımı, Revit sürümü deneme, BIM yönetmeliği eklerini okuyamadığım için uygunluk iddia etmiyorum, parapet ve mevcut binalar modelde yok. Sonraki adım: imar belgesinden otomatik parametre çıkarma. Teşekkürler."

## Prova listesi
1. Prova 1: süre ölç, takılan yeri yaz.
2. Prova 2: ≤ 5:00 değilse S-B/S-C'yi kısalt.
3. Kayıt sonrası: ses, çözünürlük, dosya açılıyor mu.
