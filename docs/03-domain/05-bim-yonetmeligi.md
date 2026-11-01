# 05 · Türkiye BIM / IFC Düzenlemesi (P6-T01 araştırması)

Araştırma tarihi: 2026-10-31. Kaynaklar aşağıda; **okunan** ile **okunamayan** ayrıdır.

## Bulunan düzenleme
**Mimarlık ve Mühendislik Projelerinin Dijital Olarak Hazırlanması Hakkında Yönetmelik** — Çevre, Şehircilik ve İklim Değişikliği Bakanlığı, Resmî Gazete 05.08.2026, sayı 33331. Görev tanımındaki "yeni BIM yönetmeliği" büyük olasılıkla budur (bu eşleşme **çıkarımdır**, görev metninde yönetmelik adı yok).

Ayrıca "Mimarlık ve Mühendislik Projelerinin Elektronik Ortamda Teslimi ve Yönetilmesi Hakkında Yönetmelik" (e-PYS) yayımlandı; haberlere göre yürürlüğü 1.9.2028. Bu belge kapsamında **okunmadı**.

## Metinden okunanlar (yönetmeliğin maddeleri, tam metin sayfasından)
| Madde | İçerik |
|---|---|
| 1 | Yapı ruhsatı için teslim edilen mimari, statik, elektrik, tesisat projelerinin dijital hazırlanması; uygulama imar planı olan alanlarda yeni binalar. Kapsam dışı: bodrum hariç ≤ 2 katlı ve ≤ 200 m² müstakil yapılar; tarım/hayvancılık yapıları |
| 3 | **BIM nesnesi** = IFC şemasında tanımlı bir varlığın modeldeki geometrik+alfanümerik örneği. **IFC** = TS EN ISO 16739-1'de tanımlı veri şeması |
| 4(4), 4(5) | BIM tabanlı oluşturma (TS EN ISO 19650-1/-2'ye atıf) ve **modelin IFC formatında teslimi** |
| 7(2) | Mahal numarası kat, mahal bölümü/fonksiyonu ve sıra numarasını içerir (EK-3'e göre) |
| 9(1), 9(2) | Model IFC; CAD çizimleri PDF/A; **tüm ölçüler SI** |
| 10(2) | Mahal isimleri EK-5'e göre |
| 11 | **Varlık adları üç alan**: disiplin, kategori, açıklama; açıklama alanında bilgiler boşluksuz, "-" ile ayrılır |
| 12 | Her varlık EK-5'teki zorunlu/isteğe bağlı **IFC sınıfları** altında; zorunlu sınıfların öznitelik ve özellikleri EK-6'da |
| 13, 14, 15 | Proje öznitelikleri EK-7; model gelişim seviyesi EK-8; model kalite kontrol formları EK-9 |
| 16, Geçici 1 | Yürürlük **1.9.2027**; BIM/IFC teslimi kademeli: büyük kentlerde 10.000 m² üstü binalarda 2029–2031, **diğer binalar 1.9.2032'ye kadar uygulanmaz**; konut ve ticaret+konut dışı binalar için 1.9.2033 |

Yönetmelik IFC **sürümünü** gövde metninde belirtmiyor (yalnız TS EN ISO 16739-1). ISO 16739-1:2018'in IFC4 ailesine karşılık geldiği genel bilgidir; yönetmelikten alınmış bir hüküm değildir.

## Okunamayanlar (dürüstlük)
- **EK-1…EK-9** (zorunlu IFC sınıfları, öznitelik/özellik adları, mahal adları, gelişim seviyesi, kontrol formları) Resmî Gazete'de `20260805-2-1.pdf` olarak yayımlı; dosya 10 MB sınırını aştığı için otomatik okunamadı. İçerikleri **doğrulanmadı**.
- Bu yüzden `data/rules/project.ids` yönetmeliğin ekleriyle eşleşme iddia etmez: **genel IFC4 profili**dir. Yönetmelik metninden doğrulanan kurallar (SI birim, mahal adı/numarası, IFC hiyerarşisi) ayrı işaretlenir.
- Yürürlük 1.9.2027 olduğundan bu proje için (3 katlı, 2 blok, ~1460 m², Konya) **zorunlu değil**; "yönetmeliğe hazırlık" olarak sunulur.

## Kaynaklar
- Tam metin (gövde): https://www.alomaliye.com/2026/08/05/mimarlik-ve-muhendislik-projelerinin-dijital-olarak-hazirlanmasi-hakkinda-yonetmelik/
- Resmî Gazete 05.08.2026 (içindekiler → yönetmelik sayfası): https://www.resmigazete.gov.tr/eskiler/2026/08/20260805-2.htm ; ekler PDF: https://www.resmigazete.gov.tr/eskiler/2026/08/20260805-2-1.pdf
- Bakanlık BIM entegrasyonu çalıştayı raporu: https://webdosya.csb.gov.tr/db/meslekihizmetler/menu/turkiye-nin-bim-entegrasyonu-calistay-raporu_20250711052344.pdf
