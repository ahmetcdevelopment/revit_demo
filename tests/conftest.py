import pytest

from brain.parcel import assign_roles, parcel_from_local_ring
from brain.schemas import ParcelSource, ZoningParams

SYN = ParcelSource(type="synthetic", note="unit test")


def make_parcel(ring, roles):
    p = parcel_from_local_ring("test", ring, source=SYN)
    return assign_roles(p, roles)


@pytest.fixture
def rect():
    """20 x 30 m; edge0 = bottom/front, 1 = right/party, 2 = top/rear, 3 = left/party."""
    return make_parcel(
        [(0, 0), (20, 0), (20, 30), (0, 30)],
        {0: {"role": "front"}, 1: {"role": "side_party"}, 2: {"role": "rear"},
         3: {"role": "side_party"}},
    )


@pytest.fixture
def params():
    return ZoningParams.model_validate({
        "source_doc": {"type": "demo_assumption"},
        "nizam": "bitisik", "taks": 0.4, "kaks": 1.2, "hmax_m": 10.5, "kat_adedi_max": 3,
        "setbacks": {"front": 5, "side_free": 3, "side_party": 0, "rear": 3},
    })
