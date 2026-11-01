from collections import Counter

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as ue
import ifcopenshell.util.placement
import numpy as np
import pytest
from shapely.geometry import LineString

from brain.backends import IfcBackend
from tests.test_planner import parcel, spec, zoning  # noqa: F401


@pytest.fixture(scope="module")
def ifc(spec, tmp_path_factory):
    path = IfcBackend().write(spec, tmp_path_factory.mktemp("ifc") / "model.ifc")
    return ifcopenshell.open(str(path))


def test_hierarchy_and_counts(ifc, spec):
    c = Counter(e.is_a() for e in ifc)
    assert c["IfcProject"] == c["IfcSite"] == c["IfcBuilding"] == 1
    assert c["IfcBuildingStorey"] == 4
    assert c["IfcWall"] == len(spec.walls)
    assert c["IfcSlab"] == len(spec.slabs) and c["IfcRoof"] == len(spec.roofs)
    assert c["IfcStair"] == len(spec.stairs) and c["IfcSpace"] == len(spec.rooms)
    assert c["IfcDoor"] == sum(o.kind == "door" for o in spec.openings)
    assert c["IfcWindow"] == sum(o.kind == "window" for o in spec.openings)
    holes = sum(len(s.openings) for s in spec.slabs)
    assert c["IfcRelVoidsElement"] == len(spec.openings) + holes
    assert c["IfcRelFillsElement"] == len(spec.openings)


def test_project_carries_spec_id(ifc, spec):
    assert spec.spec_id in ifc.by_type("IfcProject")[0].Description


def test_wall_geometry_matches_centreline(ifc, spec):
    settings = ifcopenshell.geom.settings()
    for wid in ("W-L0-B1-FRONT", "W-L1-B2-PARTY-R", "W-L2-B1-A-HOL~CORE-LOBBY"):
        w = next(x for x in spec.walls if x.id == wid)
        el = next(e for e in ifc.by_type("IfcWall") if e.Name == wid)
        local = np.array(ifcopenshell.geom.create_shape(settings, el).geometry.verts).reshape(-1, 3)
        m = ifcopenshell.util.placement.get_local_placement(el.ObjectPlacement)
        v = (m @ np.c_[local, np.ones(len(local))].T).T[:, :3]
        exp = LineString([w.a, w.b]).buffer(w.thickness / 2, cap_style="flat").bounds
        got = (v[:, 0].min(), v[:, 1].min(), v[:, 0].max(), v[:, 1].max())
        assert got == pytest.approx(exp, abs=2e-3), wid
        elev = {"L0": 0.0, "L1": 3.0, "L2": 6.0}[w.level]
        assert (v[:, 2].min(), v[:, 2].max()) == pytest.approx((elev, elev + w.height), abs=1e-3)


def test_space_area_quantities_match_spec(ifc, spec):
    from shapely.geometry import Polygon
    spaces = {s.LongName: s for s in ifc.by_type("IfcSpace")}
    for r in spec.rooms[:: max(1, len(spec.rooms) // 12)]:
        q = ue.get_psets(spaces[r.id], qtos_only=True)["Qto_SpaceBaseQuantities"]
        assert q["NetFloorArea"] == pytest.approx(Polygon(r.outline).area, abs=1e-3)
