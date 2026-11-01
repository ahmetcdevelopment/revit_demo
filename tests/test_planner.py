import pytest

from brain.neighbors import classify_edge, roles_from_evidence
from brain.planner import PlanningError, plan_building, stair_numbers
from tests.helpers import load_demo_zoning, load_real_parcel, load_synthetic


@pytest.fixture(scope="module")
def parcel():
    return load_real_parcel()


@pytest.fixture(scope="module")
def zoning():
    return load_demo_zoning()


@pytest.fixture(scope="module")
def spec(parcel, zoning):
    return plan_building(parcel, zoning)


# ---------------------------------------------------------------- edge roles from evidence
def test_classify_edge():
    assert classify_edge(["a", "a", "a"]) == "neighbor"
    assert classify_edge([None, None, None]) == "public"
    assert classify_edge(["a", None, "a"]) == "mixed"


def test_roles_follow_neighbour_evidence(parcel):
    by = {e.i: (e.role.value, e.adjacent.value) for e in parcel.edges}
    assert all(by[i] == ("side_party", "neighbor_parcel") for i in (0, 1, 2, 3, 4, 6, 7, 8))
    assert all(by[i] == ("front", "road") for i in (5, 9, 10))


def test_mixed_evidence_is_rejected():
    with pytest.raises(ValueError):
        roles_from_evidence({"edges": {"0": {"hits": ["a", None, "a"]}}})


# ---------------------------------------------------------------- real parcel plan
def test_two_blocks_fit_taks_and_kaks(spec, parcel, zoning):
    area = parcel.area_tapu_m2
    assert spec.derived.blocks == 2
    assert spec.derived.footprint_area_m2 <= zoning.taks * area + 1e-6
    assert spec.derived.gross_area_m2 <= zoning.kaks * area + 1e-6
    assert spec.derived.taks > 0.38 and spec.derived.kaks > 1.15      # uses the allowance


def test_blocks_keep_madde_24_distance(spec):
    assert spec.derived.block_gap_m >= 6.0


def test_blocks_sit_at_the_road_ends(spec):
    assert [b.road_end for b in spec.blocks] == ["min", "max"]
    assert all(b.width >= 16.6 for b in spec.blocks)
    assert all(11.8 <= b.depth <= 14.0 for b in spec.blocks)


def test_party_sides_are_close_to_the_boundary(spec):
    assert spec.derived.party_gap_max_m <= 0.6
    assert sum(b.party_left + b.party_right for b in spec.blocks) >= 3


def test_counts(spec):
    assert [lv.id for lv in spec.levels] == ["L0", "L1", "L2", "R"]
    assert len(spec.rooms) == 2 * 3 * 17
    assert len(spec.stairs) == 4 and len(spec.slabs) == 6 and len(spec.roofs) == 2
    assert sum(o.role == "flat_entry" for o in spec.openings) == 2 * 3 * 2
    assert sum(o.role == "main_entry" for o in spec.openings) == 2


def test_plan_is_deterministic(parcel, zoning, spec):
    again = plan_building(parcel, zoning)
    assert again.spec_id == spec.spec_id
    assert again.model_dump_json() == spec.model_dump_json()


def test_spec_id_changes_with_content(parcel, zoning, spec):
    assert plan_building(parcel, zoning, floor_height=2.8).spec_id != spec.spec_id
    assert plan_building(parcel, zoning, ends=["min"]).spec_id != spec.spec_id


def test_single_block_option(parcel, zoning):
    s = plan_building(parcel, zoning, ends=["min"])
    assert s.derived.blocks == 1 and s.derived.block_gap_m is None
    assert len(s.rooms) == 3 * 17


def test_no_openings_in_party_walls(spec):
    party = {w.id for w in spec.walls if w.type == "party"}
    assert party and not [o for o in spec.openings if o.host_wall in party]


def test_stair_numbers_follow_paiy():
    risers, r, b, zone = stair_numbers(3.0)
    assert sum(risers) == 19 and r <= 0.16 and b >= 0.27
    assert 60 <= (2 * r + b) * 100 <= 64
    assert zone == pytest.approx(4.0)


def test_slab_openings_only_above_ground(spec):
    for s in spec.slabs:
        assert bool(s.openings) == (s.level != "L0")


# ---------------------------------------------------------------- synthetic regression parcel
def test_synthetic_single_block(zoning):
    p = load_synthetic("synthetic_22x40.manual.json")
    s = plan_building(p, zoning, ends=["min"])
    assert s.blocks[0].party_left and s.blocks[0].party_right and s.derived.party_gap_max_m == 0
    assert s.derived.taks == pytest.approx(0.35)


def test_two_blocks_rejected_when_taks_leaves_no_depth(zoning):
    p = load_synthetic("synthetic_22x40.manual.json")
    with pytest.raises(PlanningError):
        plan_building(p, zoning)


def test_small_parcel_is_rejected(zoning):
    with pytest.raises(PlanningError):
        plan_building(load_synthetic("synthetic_12x25.manual.json"), zoning, ends=["min"])
