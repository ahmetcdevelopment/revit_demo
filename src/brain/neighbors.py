"""Edge roles from neighbour evidence (TKGM point queries), not from guesses.

An edge whose outer side hits another parcel is a party (neighbour) edge; an edge whose outer
side hits no parcel is public land (road/park) and takes the road-side setback
(PAİY Madde 23(1)(a): "yol kenarına rastlayan bahçe mesafeleri ... en az 5.00 m").
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .parcel import assign_roles
from .schemas import ParcelSpec


def classify_edge(hits: list[str | None]) -> str:
    found = [h for h in hits if h]
    if len(found) == len(hits):
        return "neighbor"
    if not found:
        return "public"
    return "mixed"


def roles_from_evidence(evidence: dict[str, Any]) -> dict[int, dict[str, Any]]:
    roles: dict[int, dict[str, Any]] = {}
    for key, info in evidence["edges"].items():
        kind = classify_edge(info["hits"])
        if kind == "mixed":
            raise ValueError(f"edge {key}: mixed evidence {info['hits']}; needs manual review")
        if kind == "neighbor":
            roles[int(key)] = {"role": "side_party", "adjacent": "neighbor_parcel"}
        else:
            roles[int(key)] = {"role": "front", "adjacent": "road"}
    return roles


def apply_evidence(parcel: ParcelSpec, path: str | Path) -> ParcelSpec:
    evidence = json.loads(Path(path).read_text(encoding="utf-8"))
    roles = roles_from_evidence(evidence)
    missing = {e.i for e in parcel.edges} - set(roles)
    if missing:
        raise ValueError(f"no evidence for edges {sorted(missing)}")
    confirmed = evidence.get("user_confirmed", {}).get("road_edges")
    if confirmed is not None:
        derived_roads = sorted(i for i, r in roles.items() if r["adjacent"] == "road")
        if derived_roads != sorted(confirmed):
            raise ValueError(f"evidence says roads {derived_roads}, user confirmed {sorted(confirmed)}")
    return assign_roles(parcel, roles)
