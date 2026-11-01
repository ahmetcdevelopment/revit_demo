from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Pt = tuple[float, float]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EdgeRole(StrEnum):
    FRONT = "front"
    REAR = "rear"
    SIDE_PARTY = "side_party"
    SIDE_FREE = "side_free"
    UNKNOWN = "unknown"


class Adjacent(StrEnum):
    ROAD = "road"
    NEIGHBOR_PARCEL = "neighbor_parcel"
    OPEN = "open"
    UNKNOWN = "unknown"


class Edge(Strict):
    i: int
    a: Pt
    b: Pt
    length: float
    role: EdgeRole = EdgeRole.UNKNOWN
    adjacent: Adjacent = Adjacent.UNKNOWN
    road_name: str | None = None
    road_width_m: float | None = None


class Admin(Strict):
    il: str
    ilce: str
    mahalle: str
    ada: int
    parsel: int


class ParcelSource(Strict):
    type: Literal["tkgm", "manual", "synthetic"]
    retrieved: str | None = None
    url: str | None = None
    fixture: str | None = None
    note: str | None = None


class CrsInfo(Strict):
    input: str
    projected: str
    local_origin_lonlat: Pt


class ValidationIssue(Strict):
    level: Literal["error", "warn"]
    code: str
    message: str


class ParcelSpec(Strict):
    schema_version: str = "1.0"
    parcel_id: str
    source: ParcelSource
    admin: Admin | None = None
    crs: CrsInfo | None = None
    ring_local: list[Pt] = Field(min_length=3)
    area_tapu_m2: float | None = None
    area_computed_m2: float
    edges: list[Edge]
