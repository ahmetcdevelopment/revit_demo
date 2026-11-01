"""Named inputs shipped with the repo: parcels, zoning parameter sets, rule tables.

A parcel name is the stem of a file in data/parcels: `<name>.geojson` (TKGM Feature, optional
`<name>.neighbors.json` evidence) or `<name>.manual.json` (hand-made local ring, used by tests).
"""

from __future__ import annotations

import json
from pathlib import Path

from .neighbors import apply_evidence
from .parcel import assign_roles, parcel_from_geojson, parcel_from_local_ring
from .rules import Rule, load_rules
from .schemas import ParcelSource, ParcelSpec, ZoningParams
from .zoning import load_zoning

ROOT = Path(__file__).resolve().parents[2]
PARCEL_DIR = ROOT / "data" / "parcels"
ZONING_DIR = ROOT / "data" / "imar-durumu"
RULES_FILE = ROOT / "data" / "rules" / "paiy-2017.yaml"
OUT_DIR = ROOT / "out"


class CatalogError(ValueError):
    """Unknown name or unreadable fixture; the message lists what is available."""


def list_parcels() -> list[str]:
    names = {p.stem for p in PARCEL_DIR.glob("*.geojson")}
    names |= {p.name.removesuffix(".manual.json") for p in PARCEL_DIR.glob("*.manual.json")}
    return sorted(names)


def list_zonings() -> list[str]:
    return sorted(p.stem for p in ZONING_DIR.glob("*.yaml"))


def load_parcel(name: str) -> ParcelSpec:
    geo = PARCEL_DIR / f"{name}.geojson"
    manual = PARCEL_DIR / f"{name}.manual.json"
    if geo.exists():
        feature = json.loads(geo.read_text(encoding="utf-8"))
        tapu = None
        alan = feature.get("properties", {}).get("alan")
        if alan:
            tapu = float(str(alan).replace(".", "").replace(",", "."))
        parcel = parcel_from_geojson(feature, name, source=ParcelSource(type="tkgm"), area_tapu_m2=tapu)
        evidence = PARCEL_DIR / f"{name}.neighbors.json"
        return apply_evidence(parcel, evidence) if evidence.exists() else parcel
    if manual.exists():
        d = json.loads(manual.read_text(encoding="utf-8"))
        p = parcel_from_local_ring(d["parcel_id"], [tuple(x) for x in d["ring_local"]],
                                   source=ParcelSource(**d["source"]), area_tapu_m2=d.get("area_tapu_m2"))
        return assign_roles(p, {int(k): v for k, v in d["roles"].items()})
    raise CatalogError(f"unknown parcel '{name}'. Available: {', '.join(list_parcels())}")


def load_zoning_params(name_or_path: str = "demo") -> ZoningParams:
    path = ZONING_DIR / f"{name_or_path}.yaml"
    if not path.exists():
        path = Path(name_or_path)
    if not path.exists():
        raise CatalogError(f"unknown zoning '{name_or_path}'. Available: {', '.join(list_zonings())}")
    return load_zoning(path)


def load_default_rules() -> dict[str, Rule]:
    return load_rules(RULES_FILE)
