# 01 · Ortam Durumu (2026-10-28 tespiti)

Makine: Windows 11 Pro 10.0.26200 · RAM ≈ 31,7 GB · GPU: NVIDIA RTX 4050 Laptop + Intel UHD
| Araç | Durum | Not |
|---|---|---|
| Python | **YOK** | `python.exe` yalnızca Microsoft Store yönlendirmesi; gerçek Python kurulu değil. `py` launcher da yok |
| Node.js | v22.18.0 ✔ | viewer için yeterli |
| .NET SDK | 9.0.305, 10.0.100, 10.0.401 (+ 10.0.100-rc.1) ✔ | Revit 2027 için .NET 10 SDK mevcut |
| Git | 2.51.0 ✔ | Klasör henüz git deposu değil (`git init` P0'da) |
| VS Code | ✔ | |
| Visual Studio | `C:\Program Files\Microsoft Visual Studio\` altında `2022` ve `18` klasörleri var | Hangi iş yükleri kurulu **doğrulanmadı**; `dotnet build` yeterli, VS şart değil |
| Autodesk/Revit | **YOK** | `C:\Program Files\Autodesk` yok |

## P0 sonrası güncelleme (2026-10-28)
- Disk: C: üzerinde ≈ 123 GB boş (Revit için yeterli).
- `winget` var. `uv 0.13.6` kuruldu; Python **3.12.16** uv yönetiminde. Not: `uv python install` bir "minor version link" uyarısı verdi; Python çalışıyor, `uv sync`/`uv run` sorunsuz.
- Not: Yeni kabuklarda `uv` PATH'te; mevcut oturumda PATH yenilenmemişse `$env:Path` yenile.
- Bağımlılıklar kurulu: pydantic 2.14, shapely 2.2, pyproj 3.8, ifcopenshell 0.9.0, ifctester, pyyaml, jinja2, mcp, pytest, ruff.
- C# iskeleti derleniyor: `net10.0-windows` + `Nice3point.Revit.Api.RevitAPI/RevitAPIUI 2027.3.0` (Revit kurulu olmadan). NuGet paketleri `net10.0-windows` ister; düz `net10.0` olmaz.

## Sonuçlar
- Python kurulumu gerekiyor → P0-T03 (kullanıcı onayı: kurulum sistem değişikliğidir).
- .NET tarafı hazır; Revit kurulumunu beklemeden add-in derlenebilir (NuGet API paketleri, bkz. karar D08).
- Donanım, Revit 2027 için yeterli görünüyor (RAM bol, ayrık GPU var). Disk boş alanı P0'da ölç: Revit indirmesi ~16 GB'a kadar, kurulu hali daha fazla.
