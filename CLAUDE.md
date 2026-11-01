# CLAUDE.md — Ajan Çalışma Kuralları (HER OTURUMDA İLK OKUNUR)

## Proje
Claude ↔ Revit köprüsü: parselden imar kontrolüyle 3 katlı bitişik nizam apartmanı Revit'te üreten, test motoru ve IFC/IDS doğrulaması olan sistem. **Bütçe 0 TL.**

## Oturum başlangıç ritüeli
1. `PROGRESS.md` oku (şu an neredeyiz, sıradaki görev).
2. İlgili faz dosyasını `docs/07-fazlar/` içinden oku.
3. Dokunacağın alanın dokümanını oku (mimari / domain / yöntem).
4. Karar kaydına (`docs/00-genel/02-karar-kaydi.md`) aykırı bir şey yapma; gerekirse yeni karar satırı ekle.

## Oturum bitiş ritüeli
`PROGRESS.md`'yi güncelle: biten görevler ☑, sürenler ▶, bulgular, bir sonraki adım, kullanıcıdan beklenenler.

## Dokümanlar
- `docs/00-genel/` vizyon-kapsam, karar kaydı, risk
- `docs/01-ortam/` ortam durumu, Revit lisans/kurulum
- `docs/02-mimari/` sistem mimarisi, veri şemaları, Revit add-in tasarımı
- `docs/03-domain/` parsel/koordinat, imar kuralları, bina programı
- `docs/04-teknoloji/` tech stack
- `docs/05-yontemler/` test stratejisi, geometri yöntemleri
- `docs/06-senaryolar/` demo senaryoları + video planı
- `docs/07-fazlar/` P0…P7 görevleri

## Değişmez kurallar
1. **Plan önce:** Kullanıcı açıkça "başla" demeden bir faz görevine kod yazma. Plan dosyaları güncellenebilir.
2. **Dürüstlük:** Doğrulanmamış imar değerleri `verified:false`; Revit'te çalıştırılmamış kod "test edildi" değildir; demo varsayımları etiketlenir.
3. **Para yok:** Ücretli servis/API/lisans önerme; kart isteyen akışta dur ve kullanıcıya sor.
4. **Dış dünya:** İndirme, kurulum, GitHub'a yükleme, hesap işlemleri → kullanıcı onayı. Parolaları/anahtarları asla girme.
5. **Deterministik çekirdek:** Geometriyi LLM değil derleyici üretir; ID'ler kararlı.
6. **Tek kaynak:** Aynı bilgiyi iki yerde tutma; çelişki görürsen dokümanı düzelt ve PROGRESS'e yaz.
7. **Dil:** Doküman Türkçe, kod/identifier İngilizce.
8. **Bellek notu:** Uzun işte bağlam kaybolabilir → karar, bulgu ve tuzakları anında dokümana yaz.

## Ortam hatırlatması (2026-10-28 tespiti)
Python YOK (kurulacak, uv ile) · Node 22 ✔ · .NET 9 ve 10 SDK ✔ · Git ✔ · Revit YOK (kurulacak) · PowerShell birincil kabuk.
