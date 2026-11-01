from collections import Counter

from brain.compiler import compile_spec
from brain.validate import validate_spec
from tests.helpers import RULES
from tests.test_planner import parcel, spec, zoning  # noqa: F401  (fixtures)


def test_planned_spec_validates_clean(spec, parcel, zoning):
    res = validate_spec(spec, parcel=parcel, params=zoning, rules=RULES)
    assert res.errors() == [], res.errors()
    assert res.ok and res.zoning.verdict == "pass"
    assert [i for i in res.issues if i.level == "warn"] == []


def test_zoning_results_are_assumed_without_belge(spec, parcel, zoning):
    st = {c.id: c.status for c in validate_spec(spec, parcel=parcel, params=zoning, rules=RULES).zoning.checks}
    assert st["Z-TAKS"] == "assumed" and st["Z-KAKS"] == "assumed"
    assert st["Z-PAIY-M23-ON"] == "pass"       # verified against the official text


def test_duplicate_id_detected(spec):
    bad = spec.model_copy(update={"walls": spec.walls + [spec.walls[0]]})
    assert "S-DUP-ID" in {i.code for i in validate_spec(bad).errors()}


def test_opening_off_wall_detected(spec):
    o = spec.openings[0]
    moved = o.model_copy(update={"at": (o.at[0] + 2.0, o.at[1] + 2.0)})
    bad = spec.model_copy(update={"openings": [moved] + spec.openings[1:]})
    assert "S-OPENING-OFF-WALL" in {i.code for i in validate_spec(bad).errors()}


def test_window_in_party_wall_detected(spec):
    w = next(w for w in spec.walls if w.type == "party")
    mid = ((w.a[0] + w.b[0]) / 2, (w.a[1] + w.b[1]) / 2)
    o = spec.openings[0].model_copy(update={"id": "O-X", "host_wall": w.id, "at": mid,
                                            "level": w.level, "kind": "window"})
    bad = spec.model_copy(update={"openings": spec.openings + [o]})
    assert "S-PARTY-OPENING" in {i.code for i in validate_spec(bad).errors()}


def test_overlapping_openings_detected(spec):
    o = next(o for o in spec.openings if o.kind == "window")
    twin = o.model_copy(update={"id": "O-TWIN"})
    bad = spec.model_copy(update={"openings": spec.openings + [twin]})
    assert "S-OPENING-OVERLAP" in {i.code for i in validate_spec(bad).errors()}


def test_removing_a_flat_entry_makes_rooms_unreachable(spec):
    gone = "O-L1-B1-A-ENTRY"
    assert any(o.id == gone for o in spec.openings)
    bad = spec.model_copy(update={"openings": [o for o in spec.openings if o.id != gone]})
    assert "C-UNREACHABLE" in {i.code for i in validate_spec(bad).errors()}


def test_undersized_room_violates_paiy(spec):
    r = next(r for r in spec.rooms if r.type == "bedroom")
    xs, ys = [p[0] for p in r.outline], [p[1] for p in r.outline]
    tiny = [(min(xs), min(ys)), (min(xs) + 1, min(ys)), (min(xs) + 1, min(ys) + 1), (min(xs), min(ys) + 1)]
    bad = spec.model_copy(update={"rooms": [x.model_copy(update={"outline": tiny}) if x is r else x
                                            for x in spec.rooms]})
    codes = {i.code for i in validate_spec(bad, rules=RULES).errors()}
    assert {"M-AREA", "M-SHORT"} <= codes


def test_bedroom_without_window_detected(spec):
    bad = spec.model_copy(update={"openings": [o for o in spec.openings if o.id != "O-L0-B1-A-BED2-1"]})
    assert "M-NO-WINDOW" in {i.code for i in validate_spec(bad, rules=RULES).errors()}


def test_blocks_too_close_detected(spec):
    shift = (-(spec.derived.block_gap_m - 3.0), 0.0)   # slide block 2 towards block 1 along x is not exact;
    # instead shrink the gap by moving every block-2 footprint point towards block 1's centroid
    from shapely.geometry import Polygon
    c1 = Polygon(spec.footprints[0]).centroid
    f2 = spec.footprints[1]
    c2 = Polygon(f2).centroid
    dx, dy = c1.x - c2.x, c1.y - c2.y
    norm = (dx * dx + dy * dy) ** 0.5
    k = (spec.derived.block_gap_m - 3.0) / norm
    moved = [(x + dx * k, y + dy * k) for x, y in f2]
    bad = spec.model_copy(update={"footprints": [spec.footprints[0], moved]})
    assert shift and "B-GAP" in {i.code for i in validate_spec(bad, rules=RULES).errors()}


def test_taks_violation_is_reported(spec, parcel, zoning):
    tight = type(zoning).model_validate({**zoning.model_dump(), "taks": 0.3})
    res = validate_spec(spec, parcel=parcel, params=tight, rules=RULES)
    assert not res.ok and "Z-TAKS" in {i.code for i in res.errors()}


def test_compile_order_and_determinism(spec):
    ops = compile_spec(spec)
    assert [o.model_dump_json() for o in ops] == [o.model_dump_json() for o in compile_spec(spec)]
    emitted = set()
    for o in ops:
        assert set(o.depends_on) <= emitted, o
        emitted.add(o.spec_ref)
    assert [o.op_id for o in ops] == [f"{i:04d}" for i in range(1, len(ops) + 1)]


def test_compile_counts(spec):
    c = Counter(o.op for o in compile_spec(spec))
    assert c["create_level"] == 4 and c["create_floor"] == 6 and c["create_stair"] == 4
    assert c["create_roof"] == 2 and c["create_room"] == len(spec.rooms)
    assert c["create_wall"] == len(spec.walls)
    assert c["place_door"] + c["place_window"] == len(spec.openings)
    assert c["create_brick_panel"] == sum(1 for w in spec.walls if w.type == "ext_brick" and w.facade)  # front, rear, free sides


def test_every_op_references_a_spec_item(spec):
    ids = ({lv.id for lv in spec.levels} | {w.id for w in spec.walls} | {s.id for s in spec.slabs}
           | {s.id for s in spec.stairs} | {r.id for r in spec.rooms}
           | {o.id for o in spec.openings} | {r.id for r in spec.roofs})
    for o in compile_spec(spec):
        assert o.spec_ref in ids or o.spec_ref.startswith(("BP-W-", "TAG-R-"))
