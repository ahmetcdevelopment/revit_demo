# 01 · Teknoloji Yığını

Tüm araçlar **ücretsiz / açık kaynak**. Sürümler kurulum sırasında `pyproject.toml` / `*.csproj` / `package.json` içinde **sabitlenir** (burada tahmin sürüm yazmıyoruz).

| Katman | Araç | Neden | Maliyet |
|---|---|---|---|
| LLM istemcisi | Claude Desktop / Claude Code (mevcut abonelik) + MCP | API ücreti yok | 0 (mevcut) |
| Beyin dili | Python 3.12 (uv ile) | Geometri/IFC ekosistemi | 0 |
| Paket/ortam | `uv` | Tek komut kurulum, kilit dosyası | 0 |
| MCP SDK | `mcp` (resmi Python SDK) | stdio sunucu | 0 |
| Şema | `pydantic` v2 | Doğrulama + JSON Schema | 0 |
| Geometri | `shapely` | Poligon, kesişim, offset | 0 |
| Koordinat | `pyproj` | ITRF96/TM ↔ WGS84 | 0 |
| IFC | `ifcopenshell` | IFC4 okuma/yazma/doğrulama | 0 |
| IDS | `ifctester` (IfcOpenShell) | IDS ile doğrulama | 0 |
| Kural | `pyyaml` (+ `jsonschema`) | Madde atıflı kurallar | 0 |
| Rapor | `jinja2` + saf SVG | Bağımsız HTML rapor | 0 |
| Test | `pytest`, `hypothesis` (opsiyonel) | Özellik tabanlı testler | 0 |
| Kalite | `ruff`, `mypy` (opsiyonel) | | 0 |
| Revit add-in | C# · .NET (Revit sürümüne göre 10/8) · `Nice3point.Revit.Api.*` NuGet | API derleme referansı | 0 |
| Revit | 30 gün deneme **veya** Education planı | Hedef platform | 0 |
| IFC viewer | Node 22 + `@thatopen/components` / `web-ifc` + Vite | Tarayıcıda gezinme (S1) | 0 |
| CI | GitHub Actions (public repo) | Testler Revit'siz | 0 |
| Video | OBS Studio | Ekran kaydı | 0 |
| Diyagram | Mermaid (README içinde) | | 0 |

## Mevcut makinede
Node 22.18 ✔ · .NET SDK 9/10 ✔ · Git ✔ · Python ✘ (kurulacak) · Revit ✘ (kurulacak).

## Kurulum komutları (P0'da, kullanıcı onayıyla)
```powershell
winget install --id astral-sh.uv -e          # uv
uv python install 3.12                        # Python
```
`winget` yoksa uv kurucu betiği veya python.org. Revit için tarayıcı akışı (bkz. 01-ortam).

## Proje düzeni (kök)
```
revit_demo/
├─ README.md · CLAUDE.md · PROGRESS.md
├─ docs/                (bu planlar)
├─ src/brain/           (Python paketi: schemas, parcel, zoning, planner, compiler, verify, ifc, backends, mcp_server)
├─ src/revit-addin/     (C# çözümü)
├─ src/viewer/          (Vite + That Open, stretch)
├─ tests/               (pytest; fixtures)
├─ data/{parcels,rules,imar-durumu}/
├─ tools/               (fetch_parcel.py vb. yardımcılar)
└─ out/                 (üretilen: spec, ops, rapor, ifc, replay; git'e girmez)
```

## Neden bu seçimler
- Python'da shapely+pyproj+IfcOpenShell ile Revit'siz tüm domain mantığı test edilir → riski Revit kurulumundan ayırır.
- C# yalnız Revit'in zorunlu olduğu yerde (API) → add-in ince ve az hata yüzeyli.
- MCP stdio → Claude ile entegrasyon ek altyapı gerektirmez.
