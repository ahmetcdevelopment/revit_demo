# 04 · Önceki Çalışmalar (Prior Art)

Tarih: 2026-10-28 · Yöntem: tek web araması; yıldız/araç sayıları üçüncü taraf dizinlerden, **güncel olmayabilir**. Lisans, desteklenen Revit sürümü ve son commit tarihi **kontrol edilmedi**.

Açık kaynakta Claude↔Revit için birkaç MCP projesi var; çoğu aynı iki parçalı tasarımı kullanıyor: bir MCP sunucusu + Revit içinde çalışan C# add-in.
| Proje | Not |
|---|---|
| `revit-mcp` organizasyonu (GitHub) | Sunucu + ayrı `revit-mcp-plugin` deposu |
| Sam-AEC/Autodesk-Revit-MCP-Server | Python MCP sunucusu + C# add-in, ExternalEvent ile ana thread; 100+ araç (dizin bilgisi) |
| IbrahimFahdah/revit-claude-mcp | Claude Desktop için, Node.js + C# WPF add-in, ~46 araç |
| shuotao/REVIT_MCP_study | 167 araç, WebSocket (localhost:8964) |

## Bizim farkımız
Bu projelerin ortak yaklaşımı: LLM'e çok sayıda **düşük seviyeli araç** vermek (duvar çiz, kapı koy…). Bizim yaklaşım:
1. LLM yalnız **BuildingSpec** (yapılandırılmış niyet) üretir; geometri deterministik derleyicide.
2. **İdempotent reconcile** (spec_id) ve atomik TransactionGroup.
3. **Revit'siz test edilebilir çekirdek** (CI).
4. **Madde atıflı imar motoru** ve IDS ile IFC doğrulaması.

## Kural
Bu depolardan **kod kopyalanmaz**. Yalnız yaygın kalıpların (ExternalEvent kuyruğu gibi) varlığı doğrulama amaçlı not edilir. İlham/atıf README'de belirtilir.
