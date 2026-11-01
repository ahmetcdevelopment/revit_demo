# P0 · Ortam, Lisans, Repo İskeleti

**Amaç:** Hiçbir şeyi bloklamadan Revit indirmesini başlatmak ve geliştirme ortamını hazır hale getirmek.

| ID | Görev | Sahip | Kabul |
|---|---|---|---|
| P0-T01 | Disk boş alanını ölç; ≥ 40 GB değilse temizlik öner | Ajan | Rapor `PROGRESS.md`'de |
| P0-T02 | **Revit edinimi:** öğrenci/eğitmen misin? → Education; değilse 30 gün deneme. Kart isteniyorsa DUR | Kullanıcı | Kurulum başladı |
| P0-T03 | Python: `winget install astral-sh.uv` + `uv python install 3.12` (kullanıcı onayı) | Ajan+Kullanıcı | `uv run python --version` = 3.12.x |
| P0-T04 | `git init`, `.gitignore` (out/, bin/, obj/, .venv/, `__pycache__`), ilk commit (kullanıcı isterse) | Ajan | Temiz `git status` |
| P0-T05 | `pyproject.toml` (uv), bağımlılıkları kur: pydantic, shapely, pyproj, ifcopenshell, ifctester, pyyaml, jinja2, mcp, pytest | Ajan | `uv run pytest` (boş) geçer, `import ifcopenshell, shapely, pyproj` çalışır |
| P0-T06 | `global.json` + C# çözüm iskeleti (`dotnet new classlib`), NuGet `Nice3point.Revit.Api.*` ile **Revit'siz derleme** | Ajan | `dotnet build` yeşil |
| P0-T07 | `CLAUDE.md` ve `PROGRESS.md` oluştur (zaten var ise gözden geçir) | Ajan | Dosyalar mevcut |
| P0-T08 | Önceki çalışma (prior art) taraması: açık kaynak Revit MCP projeleri, Revit-MCP kalıpları — yalnız okuma/fikir, kopya değil | Ajan | `docs/00-genel/` notu (≤ 1 sayfa) |
| P0-T09 | Revit sürümünü not et (Help › About) ve D07'yi kesinleştir; TargetFramework seç | Kullanıcı+Ajan | Karar kaydı güncel |

**DoD:** Python+uv çalışıyor · NuGet ile C# derleniyor · Revit kurulumu başladı/bitti ve sürüm kaydedildi · iskelet commit'li.
**Riskler:** R01, R02, R12.
