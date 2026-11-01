import math

import pytest
from shapely.geometry import LineString, Polygon

from brain.zoning import buildable_polygon, check_zoning, load_zoning
from tests.conftest import make_parcel


def test_rect_party_walls_sit_on_boundary(rect, params):
    b = buildable_polygon(rect, params.setbacks)
    minx, miny, maxx, maxy = b.bounds
    assert (minx, maxx) == pytest.approx((0, 20))      # side_party = 0
    assert (miny, maxy) == pytest.approx((5, 27))      # front 5, rear 3
    assert b.area == pytest.approx(440)


def test_zero_setbacks_returns_parcel(rect, params):
    sb = params.setbacks.model_copy(update=dict(front=0, rear=0))
    assert buildable_polygon(rect, sb).area == pytest.approx(600)


def test_free_sides_use_their_own_setback(params):
    p = make_parcel([(0, 0), (20, 0), (20, 30), (0, 30)],
                    {0: {"role": "front"}, 1: {"role": "side_free"}, 2: {"role": "rear"},
                     3: {"role": "side_party"}})
    b = buildable_polygon(p, params.setbacks)
    assert b.bounds == pytest.approx((0, 5, 17, 27))


def test_trapezoid_every_edge_respects_its_setback(params):
    ring = [(0, 0), (20, 0), (15, 30), (5, 30)]
    roles = {0: {"role": "front"}, 1: {"role": "side_free"}, 2: {"role": "rear"},
             3: {"role": "side_free"}}
    p = make_parcel(ring, roles)
    b = buildable_polygon(p, params.setbacks)
    assert Polygon(ring).contains(b) or Polygon(ring).buffer(1e-9).contains(b)
    for e in p.edges:
        d = {"front": 5, "side_free": 3, "rear": 3}[e.role.value]
        line = LineString([e.a, e.b])
        # infinite-line distance from every buildable vertex must be >= setback
        dx, dy = (e.b[0] - e.a[0]) / e.length, (e.b[1] - e.a[1]) / e.length
        for x, y in b.exterior.coords:
            dist = (x - e.a[0]) * -dy + (y - e.a[1]) * dx   # signed, inward positive
            assert dist >= d - 1e-6, (e.i, dist)
        assert line.length > 0


def test_setbacks_larger_than_parcel_fail(rect, params):
    sb = params.setbacks.model_copy(update=dict(front=20, rear=20))
    p = params.model_copy(update={"setbacks": sb})
    r = check_zoning(rect, p)
    assert r.verdict == "fail" and r.buildable_area_m2 == 0


def test_taks_boundary(rect, params):
    ok = check_zoning(rect, params, footprint=[(0, 5), (20, 5), (20, 17), (0, 17)], floors=3,
                      floor_height_m=3.0)
    assert {c.id: c.status for c in ok.checks}["Z-TAKS"] == "assumed"   # 240 <= 240
    bad = check_zoning(rect, params, footprint=[(0, 5), (20, 5), (20, 18), (0, 18)], floors=3,
                       floor_height_m=3.0)
    assert {c.id: c.status for c in bad.checks}["Z-TAKS"] == "fail"     # 260 > 240
    assert bad.verdict == "fail"


def test_kaks_floors_and_height_checks(rect, params):
    fp = [(0, 5), (20, 5), (20, 15), (0, 15)]       # 200 m2
    r = check_zoning(rect, params, footprint=fp, floors=4, floor_height_m=3.0)
    st = {c.id: c.status for c in r.checks}
    assert st["Z-KAT"] == "fail" and st["Z-HMAX"] == "fail" and st["Z-KAKS"] == "fail"
    r3 = check_zoning(rect, params, footprint=fp, floors=3, floor_height_m=3.0)
    assert r3.verdict == "pass"


def test_footprint_in_setback_zone_fails(rect, params):
    r = check_zoning(rect, params, footprint=[(0, 2), (20, 2), (20, 10), (0, 10)], floors=1)
    assert {c.id: c.status for c in r.checks}["Z-SETBACK-FIT"] == "fail"


def test_unverified_rules_are_never_reported_as_pass(rect, params):
    r = check_zoning(rect, params, footprint=[(0, 5), (20, 5), (20, 10), (0, 10)], floors=2,
                     floor_height_m=3.0)
    assert r.demo_assumption
    assert all(c.status in ("assumed", "fail") for c in r.checks)


def test_verified_citation_yields_pass(rect, params):
    p = type(params).model_validate({**params.model_dump(), "citations": {
        "setbacks": {"ref": "test", "verified": True}, "taks": {"ref": "t", "verified": True}}})
    r = check_zoning(rect, p, footprint=[(0, 5), (20, 5), (20, 10), (0, 10)])
    st = {c.id: c.status for c in r.checks}
    assert st["Z-TAKS"] == "pass" and st["Z-SETBACK-FIT"] == "pass"


def test_demo_yaml_loads():
    p = load_zoning("data/imar-durumu/demo.yaml")
    assert p.source_doc.type == "demo_assumption" and math.isclose(p.taks, 0.4)
