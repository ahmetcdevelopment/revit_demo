import pytest

from brain.crs import LocalFrame
from brain.parcel import (
    assign_roles,
    clean_ring,
    parcel_from_geojson,
    parcel_from_local_ring,
    signed_area,
    validate_parcel,
)
from brain.schemas import ParcelSource

SYN = ParcelSource(type="synthetic")


def test_clockwise_ring_is_normalised_ccw_and_closing_point_dropped():
    cw = [(0, 0), (0, 30), (20, 30), (20, 0), (0, 0)]
    ring = clean_ring(cw)
    assert len(ring) == 4 and signed_area(ring) > 0


def test_area_and_edges(rect):
    assert rect.area_computed_m2 == pytest.approx(600)
    assert [round(e.length, 3) for e in rect.edges] == [20, 30, 20, 30]


def test_near_duplicate_points_merged():
    ring = clean_ring([(0, 0), (0.001, 0), (20, 0), (20, 30), (0, 30)])
    assert len(ring) == 4


def test_geojson_roundtrip_area():
    f = LocalFrame.at((32.55, 37.88))
    local = [(0, 0), (20, 0), (20, 30), (0, 30), (0, 0)]
    coords = [list(f.from_local(x, y)) for x, y in local]
    feature = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [coords]}}
    p = parcel_from_geojson(feature, "g", source=SYN)
    assert p.area_computed_m2 == pytest.approx(600, rel=2e-3)
    assert p.crs.projected == "EPSG:5255"


def test_geojson_rejects_non_turkey_coordinates():
    feature = {"type": "Feature", "geometry": {"type": "Polygon",
               "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}}
    with pytest.raises(ValueError):
        parcel_from_geojson(feature, "x", source=SYN)


def test_validate_requires_front_and_known_roles():
    p = parcel_from_local_ring("t", [(0, 0), (20, 0), (20, 30), (0, 30)], source=SYN)
    codes = {i.code for i in validate_parcel(p)}
    assert {"P-NO-FRONT", "P-ROLE-UNKNOWN"} <= codes


def test_validate_ok_for_rect(rect):
    assert validate_parcel(rect) == []


def test_bowtie_is_invalid():
    p = parcel_from_local_ring("b", [(0, 0), (20, 30), (20, 0), (0, 30)], source=SYN)
    p = assign_roles(p, {0: {"role": "front"}, 1: {"role": "rear"}, 2: {"role": "rear"},
                         3: {"role": "rear"}})
    assert "P-INVALID" in {i.code for i in validate_parcel(p)}


def test_tapu_area_mismatch_warns():
    p = parcel_from_local_ring("t", [(0, 0), (20, 0), (20, 30), (0, 30)], source=SYN,
                               area_tapu_m2=650)
    assert "P-AREA" in {i.code for i in validate_parcel(assign_roles(
        p, {0: {"role": "front"}, 1: {"role": "side_party"}, 2: {"role": "rear"},
            3: {"role": "side_party"}}))}


def test_role_for_missing_edge_rejected(rect):
    with pytest.raises(ValueError):
        assign_roles(rect, {9: {"role": "front"}})
