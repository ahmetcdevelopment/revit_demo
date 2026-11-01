"""verify_model must accept a faithful model and name every kind of deviation."""

import copy

import pytest

from brain.verify import verify
from tests.fake_revit import model_from_spec
from tests.test_planner import parcel, spec, zoning  # noqa: F401


def test_faithful_model_passes(spec):
    r = verify(spec, model_from_spec(spec))
    assert r.ok, r.differences
    assert {row.category for row in r.rows} >= {"walls", "rooms", "room area m2", "stairs", "doors", "windows"}
    assert r.revit_warnings == 3


def _mutated(spec, edit):
    m = copy.deepcopy(model_from_spec(spec))
    edit(m)
    return verify(spec, m)


def test_missing_wall_is_named(spec):
    wid = spec.walls[0].id
    r = _mutated(spec, lambda m: m["walls"].pop(0))
    assert not r.ok and any(f"wall {wid} missing" in d for d in r.differences)


def test_wall_too_short_or_too_long(spec):
    wid = spec.walls[1].id
    short = _mutated(spec, lambda m: m["walls"][1].update(length_m=m["walls"][1]["length_m"] - 0.5))
    long = _mutated(spec, lambda m: m["walls"][1].update(length_m=m["walls"][1]["length_m"] + 1.0))
    assert any(f"wall {wid} length" in d for d in short.differences)
    assert any(f"wall {wid} length" in d for d in long.differences)


def test_wrong_wall_thickness(spec):
    r = _mutated(spec, lambda m: m["walls"][0].update(thickness_m=0.5))
    assert any("thickness" in d for d in r.differences)


def test_unenclosed_room_is_reported(spec):
    rid = spec.rooms[3].id
    r = _mutated(spec, lambda m: m["rooms"][3].update(area_m2=0))
    assert any(f"room {rid} is not enclosed" in d for d in r.differences)


def test_room_area_tolerance_is_two_percent(spec):
    room = spec.rooms[0]
    from shapely.geometry import Polygon
    a = Polygon(room.outline).area
    near = _mutated(spec, lambda m: m["rooms"][0].update(area_m2=a * 1.015))
    far = _mutated(spec, lambda m: m["rooms"][0].update(area_m2=a * 1.05))
    assert not any(room.id in d for d in near.differences)
    assert any(room.id in d for d in far.differences)


def test_open_core_rooms_get_the_wider_tolerance_but_walled_rooms_do_not(spec):
    from shapely.geometry import Polygon
    core = next(r for r in spec.rooms if "-CORE-" in r.id)
    walled = next(r for r in spec.rooms if "-CORE-" not in r.id)
    ci = spec.rooms.index(core)
    wi = spec.rooms.index(walled)
    ca, wa = Polygon(core.outline).area, Polygon(walled.outline).area
    ok = _mutated(spec, lambda m: m["rooms"][ci].update(area_m2=ca * 1.03))
    bad_core = _mutated(spec, lambda m: m["rooms"][ci].update(area_m2=ca * 1.08))
    bad_walled = _mutated(spec, lambda m: m["rooms"][wi].update(area_m2=wa * 1.03))
    assert not any(core.id in d for d in ok.differences)
    assert any(core.id in d for d in bad_core.differences)
    assert any(walled.id in d for d in bad_walled.differences)


def test_stair_numbers_must_match(spec):
    r = _mutated(spec, lambda m: m["stairs"][0].update(risers=12, tread_d_m=0.25))
    sid = spec.stairs[0].id
    assert any(f"stair {sid} risers 12" in d for d in r.differences)
    assert any(f"stair {sid} tread" in d for d in r.differences)


def test_opening_counts(spec):
    def edit(m):
        m["openings"] = [o for o in m["openings"] if o["category"] != "Windows"][:]
    r = _mutated(spec, edit)
    assert not r.ok and any("windows" in d for d in r.differences)


def test_untagged_wall_in_model_is_flagged(spec):
    r = _mutated(spec, lambda m: m["walls"].append({"spec_ref": None, "length_m": 1, "thickness_m": 0.1, "height_m": 3}))
    assert any("not tagged" in d for d in r.differences)


@pytest.mark.parametrize("key", ["walls", "floors", "rooms", "stairs", "openings"])
def test_model_missing_whole_category(spec, key):
    r = _mutated(spec, lambda m: m.update({key: []}))
    assert not r.ok


def test_stair_standing_a_storey_too_high_is_caught(spec):
    """The Revit run-elevation bug (L1->L2 stairs built at 3..9 m instead of 3..6 m) must be visible."""
    st = next(s for s in spec.stairs if s.from_level == "L1")
    i = spec.stairs.index(st)
    r = _mutated(spec, lambda m: m["stairs"][i].update(z_min_m=3.0, z_max_m=9.0))
    assert not r.ok and any(f"stair {st.id} stands at z" in d for d in r.differences)


def test_klinker_panel_piece_counts_are_compared(spec):
    from brain.brick import expected_pieces
    from brain.compiler import compile_spec
    want = expected_pieces(compile_spec(spec), "courses")
    ref = next(iter(want))
    m = model_from_spec(spec)
    assert verify(spec, m, brick_expected=want).ok
    m["brick_panels"][0]["comments"] = "klinker pieces=1; faces=5; lod=courses"
    r = verify(spec, m, brick_expected=want)
    assert not r.ok and any(ref in d and "pieces" in d for d in r.differences)
    m["brick_panels"].pop(1)
    assert any("missing in model" in d for d in verify(spec, m, brick_expected=want).differences)
