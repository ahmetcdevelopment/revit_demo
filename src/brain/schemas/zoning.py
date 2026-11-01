from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .parcel import Pt


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Citation(Strict):
    ref: str
    verified: bool = False


class SourceDoc(Strict):
    type: Literal["imar_durumu", "demo_assumption"]
    file: str | None = None
    date: str | None = None


class Setbacks(Strict):
    front: float = Field(ge=0)
    side_free: float = Field(ge=0)
    side_party: float = Field(ge=0)
    rear: float = Field(ge=0)


class ZoningParams(Strict):
    schema_version: str = "1.0"
    source_doc: SourceDoc
    nizam: Literal["bitisik", "ayrik", "blok"]
    taks: float = Field(gt=0, le=1)
    kaks: float = Field(gt=0)
    hmax_m: float | None = None
    kat_adedi_max: int | None = None
    setbacks: Setbacks
    # field name -> citation; missing or unverified entries make results "assumed"
    citations: dict[str, Citation] = Field(default_factory=dict)


class Check(Strict):
    id: str
    status: Literal["pass", "fail", "warn", "assumed"]
    actual: float | None = None
    limit: float | None = None
    message: str
    citation: Citation | None = None


class ZoningReport(Strict):
    parcel_id: str
    demo_assumption: bool
    buildable_polygon: list[Pt]
    buildable_area_m2: float
    limits: dict[str, float | None]
    checks: list[Check]
    verdict: Literal["pass", "fail"]
