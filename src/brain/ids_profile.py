"""The project's IDS (Information Delivery Specification) and the runner that checks an IFC against it.

Profile: **generic IFC4**. Requirements marked `source: regulation` come from the text of the Mimarlik ve
Muhendislik Projelerinin Dijital Olarak Hazirlanmasi Hakkinda Yonetmelik (RG 05.08.2026-33331) that was read
(docs/03-domain/05-bim-yonetmeligi.md); everything else is common IFC4 delivery practice. The regulation's
annexes EK-5/EK-6 (mandatory classes and attributes) could not be read, so NO claim of conformity to them is made.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import ifcopenshell
from ifctester import ids, reporter

IDS_PATH = Path(__file__).resolve().parents[2] / "data" / "rules" / "project.ids"

REGULATION = "regulation (Madde {})"
PRACTICE = "generic IFC4 practice"


def _spec(my: ids.Ids, ident: str, name: str, entity: str, reqs: list[Any], source: str, minimum: int = 1) -> None:
    s = ids.Specification(name=name, ifcVersion=["IFC4"], identifier=ident, minOccurs=minimum,
                          description=f"source: {source}")
    s.applicability.append(ids.Entity(name=entity))
    s.requirements.extend(reqs)
    my.specifications.append(s)


def attr(name: str, pattern: str | None = None) -> ids.Attribute:
    value = ids.Restriction(options={"pattern": pattern}, base="string") if pattern else None
    return ids.Attribute(name=name, value=value, cardinality="required")


def prop(pset: str, name: str) -> ids.Property:
    return ids.Property(propertySet=pset, baseName=name, cardinality="required")


def build_ids() -> ids.Ids:
    my = ids.Ids(title="Karatay 1495/26 - IFC teslim profili", author="revit-demo", version="0.1",
                 description="Genel IFC4 profili; yonetmelik EK-5/EK-6 eslemesi dogrulanmadi.",
                 purpose="IFC teslim kontrolu", milestone="Mimari proje")
    _spec(my, "S01", "Building has a name and storey count", "IFCBUILDING",
          [attr("Name", r".+"), prop("Pset_BuildingCommon", "NumberOfStoreys")], PRACTICE)
    _spec(my, "S02", "Storeys have name and elevation", "IFCBUILDINGSTOREY",
          [attr("Name", r".+"), attr("Elevation")], PRACTICE, minimum=1)
    _spec(my, "S03", "Spaces carry a name following kat-blok-daire-mahal numbering", "IFCSPACE",
          [attr("Name", r"L\d-B\d+-.+"), attr("LongName")], REGULATION.format("7(2)") + "; EK-3 not read")
    _spec(my, "S04", "Spaces have their net floor area", "IFCSPACE",
          [prop("Qto_SpaceBaseQuantities", "NetFloorArea")], PRACTICE)
    _spec(my, "S05", "Walls say whether they are external and load bearing", "IFCWALL",
          [prop("Pset_WallCommon", "IsExternal"), prop("Pset_WallCommon", "LoadBearing")], PRACTICE)
    _spec(my, "S06", "Walls have base quantities", "IFCWALL",
          [prop("Qto_WallBaseQuantities", "Length"), prop("Qto_WallBaseQuantities", "Width")], PRACTICE)
    _spec(my, "S07", "Doors have size and external flag", "IFCDOOR",
          [attr("OverallWidth"), attr("OverallHeight"), prop("Pset_DoorCommon", "IsExternal")], PRACTICE)
    _spec(my, "S08", "Windows have size and external flag", "IFCWINDOW",
          [attr("OverallWidth"), attr("OverallHeight"), prop("Pset_WindowCommon", "IsExternal")], PRACTICE)
    _spec(my, "S09", "Slabs say whether they are external", "IFCSLAB",
          [prop("Pset_SlabCommon", "IsExternal")], PRACTICE)
    _spec(my, "S10", "Stairs describe their risers and treads", "IFCSTAIR",
          [prop("Pset_StairCommon", "NumberOfRiser"), prop("Pset_StairCommon", "RiserHeight"),
           prop("Pset_StairCommon", "TreadLength")], PRACTICE)
    return my


def write_ids(path: Path = IDS_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    build_ids().to_xml(str(path))
    return path


def check_ifc(ifc_path: str | Path, ids_path: Path = IDS_PATH, html_out: Path | None = None) -> dict[str, Any]:
    """Run the IDS against an IFC file. Returns a plain summary (and writes an HTML report when asked)."""
    spec = ids.open(str(ids_path))
    model = ifcopenshell.open(str(ifc_path))
    spec.validate(model)
    rep = reporter.Json(spec)
    rep.report()
    data = rep.to_string() if hasattr(rep, "to_string") else None
    import json
    full = json.loads(data) if data else {}
    rows = []
    for s in full.get("specifications", []):
        rows.append({
            "id": s.get("identifier"), "name": s.get("name"), "status": bool(s.get("status")),
            "applicable": s.get("total_applicable", 0), "passed": s.get("total_applicable_pass", 0),
            "failed": s.get("total_applicable_fail", 0),
            "failures": [
                {"requirement": r.get("description"), "count": len(r.get("failures", []))}
                for r in s.get("requirements", []) if r.get("failures")
            ],
        })
    if html_out is not None:
        html = reporter.Html(spec)
        html.report()
        html.to_file(str(html_out))
    return {"ok": all(r["status"] for r in rows), "specifications": rows,
            "profile": "generic IFC4 (regulation annexes EK-5/EK-6 not verified)"}
