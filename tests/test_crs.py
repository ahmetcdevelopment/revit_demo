import math

import pytest
from pyproj import CRS

from brain.crs import LocalFrame, tm_epsg_for_lon


@pytest.mark.parametrize("lon,epsg", [(27.0, 5253), (29.9, 5254), (32.5, 5255), (36.0, 5256)])
def test_zone_selection(lon, epsg):
    assert tm_epsg_for_lon(lon) == epsg
    assert "TM" in CRS.from_epsg(epsg).name


def test_konya_roundtrip_is_sub_millimetre():
    f = LocalFrame.at((32.55, 37.88))
    assert f.epsg == 5255
    for x, y in [(0, 0), (100, 50), (-80.5, 120.25), (350, -400)]:
        lon, lat = f.from_local(x, y)
        x2, y2 = f.to_local(lon, lat)
        assert math.hypot(x2 - x, y2 - y) < 1e-3


def test_local_distance_close_to_geodesic():
    f = LocalFrame.at((32.55, 37.88))
    lon, lat = f.from_local(100, 0)
    # ~100 m east: scale factor of TM near the central meridian is ~1, so lon shift is sane
    assert 0 < lon - 32.55 < 0.002
