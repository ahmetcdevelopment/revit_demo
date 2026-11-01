"""BuildingSpec (central contract) and the Op list the compiler derives from it."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .parcel import Pt


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Level(Strict):
    id: str
    name: str
    elevation: float
    height: float = Field(gt=0)


class Project(Strict):
    name: str
    parcel_id: str
    north_angle_deg: float = 0.0


class BlockInfo(Strict):
    id: str
    road_end: Literal["min", "max"]
    width: float
    depth: float
    party_left: bool
    party_right: bool
    gap_left_m: float           # largest distance between that footprint side and the parcel boundary
    gap_right_m: float


class Wall(Strict):
    id: str
    level: str
    a: Pt
    b: Pt
    type: Literal["ext_brick", "party", "core", "partition"]
    thickness: float = Field(gt=0)
    height: float = Field(gt=0)
    facade: Literal["front", "rear", "side"] | None = None


class Slab(Strict):
    id: str
    level: str
    outline: list[Pt] = Field(min_length=3)
    openings: list[list[Pt]] = Field(default_factory=list)
    thickness: float = Field(gt=0)


class Stair(Strict):
    id: str
    from_level: str
    to_level: str
    run_width: float
    well_width: float
    risers: list[int]
    riser_h: float
    tread_d: float
    landing_depth: float
    origin: Pt            # world; start of run 1 (corner of the stair zone)
    direction: Pt         # unit vector along the runs
    side: Pt              # unit vector across the runs
    zone_length: float


RoomType = Literal["living", "bedroom", "kitchen", "bath", "wc", "hall", "stair", "core_hall"]


class Room(Strict):
    id: str
    name: str
    type: RoomType
    level: str
    unit: str | None = None
    outline: list[Pt] = Field(min_length=3)
    kitchen_niche: bool = False
    ventilation: Literal["natural", "mechanical"] = "natural"


class Opening(Strict):
    id: str
    kind: Literal["door", "window"]
    role: Literal["main_entry", "rear_exit", "flat_entry", "interior", "window"]
    level: str
    host_wall: str
    at: Pt                # world centre of the opening on the wall centre line
    width: float
    height: float
    sill: float = 0.0
    family_hint: str = ""


class Roof(Strict):
    id: str
    type: Literal["flat"] = "flat"
    outline: list[Pt]
    parapet_h: float
    thickness: float


class Brick(Strict):
    length: float = 0.24
    height: float = 0.052
    depth: float = 0.115
    joint: float = 0.010


class FacadeSpec(Strict):
    material: Literal["klinker"] = "klinker"
    bond: Literal["stretcher", "flemish"] = "stretcher"
    brick: Brick = Field(default_factory=Brick)
    color: str = "#8a3b2a"


class Facade(Strict):
    front: FacadeSpec = Field(default_factory=FacadeSpec)
    rear: FacadeSpec = Field(default_factory=FacadeSpec)


class Derived(Strict):
    footprint_area_m2: float
    gross_area_m2: float
    taks: float
    kaks: float
    blocks: int = 1
    block_gap_m: float | None = None
    party_gap_max_m: float | None = None


class BuildingSpec(Strict):
    schema_version: str = "1.0"
    spec_id: str = ""
    project: Project
    levels: list[Level] = Field(min_length=1)
    blocks: list[BlockInfo] = Field(default_factory=list)
    footprints: list[list[Pt]] = Field(min_length=1)
    walls: list[Wall] = Field(default_factory=list)
    slabs: list[Slab] = Field(default_factory=list)
    stairs: list[Stair] = Field(default_factory=list)
    rooms: list[Room] = Field(default_factory=list)
    openings: list[Opening] = Field(default_factory=list)
    roofs: list[Roof] = Field(default_factory=list)
    facade: Facade = Field(default_factory=Facade)
    derived: Derived | None = None
    known_gaps: list[str] = Field(default_factory=list)


OP_TYPES = (
    "create_level",
    "create_wall",
    "create_floor",
    "create_stair",
    "create_roof",
    "create_room",
    "place_door",
    "place_window",
    "create_brick_panel",
    "tag_room",
)


class Op(Strict):
    op_id: str
    op: Literal[OP_TYPES]  # type: ignore[valid-type]
    spec_ref: str
    depends_on: list[str] = Field(default_factory=list)
    args: dict[str, Any] = Field(default_factory=dict)
