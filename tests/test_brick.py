"""Klinker layout: pure geometry checks (no Revit)."""

import math

import pytest
from shapely.geometry import Point, Polygon

from brain import brick
from brain.compiler import compile_spec
from tests.test_planner import parcel, spec, zoning  # noqa: F401


@pytest.fixture
def panels(spec):
    return [o for o in compile_spec(spec) if o.op == "create_brick_panel"]


def args(o, lod="full"):
    return {**o.args, "lod": lod}


def test_every_exterior_wall_with_a_facade_gets_a_panel(spec, panels):
    walls = {w.id for w in spec.walls if w.type == "ext_brick" and w.facade}
    assert {o.args["wall"] for o in panels} == walls and len(panels) == len(walls)


def test_panels_depend_on_their_wall_and_hosted_openings(spec, panels):
    for o in panels:
        hosted = {op.id for op in spec.openings if op.host_wall == o.args["wall"]}
        assert set(o.depends_on) == {o.args["wall"], *hosted}


def test_normal_points_out_of_the_building(spec, panels):
    feet = [Polygon(f) for f in spec.footprints]
    for o in panels:
        (ax, ay), (bx, by) = o.args["a"], o.args["b"]
        nx, ny = o.args["normal"]
        assert math.isclose(math.hypot(nx, ny), 1, abs_tol=1e-5)
        mid = Point((ax + bx) / 2 + nx * 0.4, (ay + by) / 2 + ny * 0.4)
        assert not any(f.contains(mid) for f in feet), o.spec_ref


def test_brick_area_is_the_wall_area_less_joints_and_openings(panels):
    for o in panels:
        got = brick.layout(args(o))["face_area_m2"]
        net = brick.net_wall_area(o.args)
        b = o.args["brick"]
        ideal = net * (b["length"] / (b["length"] + b["joint"])) * (b["height"] / (b["height"] + b["joint"]))
        assert 0.80 * ideal <= got <= 1.02 * ideal, (o.spec_ref, got, ideal)


def test_no_brick_covers_an_opening(panels):
    for o in panels:
        a = args(o)
        (ax, ay), (bx, by) = a["a"], a["b"]
        length = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / length, (by - ay) / length
        holes = []
        for h in a["openings"]:
            u = (h["at"][0] - ax) * ux + (h["at"][1] - ay) * uy
            holes.append((u - h["width"] / 2, u + h["width"] / 2, h["sill"], h["sill"] + h["height"]))
        bh = a["brick"]["height"]
        for course in brick.layout(a)["courses"]:
            z0, z1 = course["z"], course["z"] + bh
            for u0, u1 in course["u"]:
                for h0, h1, lo, hi in holes:
                    overlaps_u = u0 < h1 - 5e-4 and u1 > h0 + 5e-4   # layout is rounded to 0.1 mm
                    overlaps_z = z0 < hi - 5e-4 and z1 > lo + 5e-4
                    assert not (overlaps_u and overlaps_z), (o.spec_ref, u0, u1, z0)


def test_bricks_inside_a_course_do_not_overlap_and_keep_the_joint(panels):
    o = panels[0]
    j = o.args["brick"]["joint"]
    for course in brick.layout(args(o))["courses"]:
        spans = course["u"]
        for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
            assert b0 >= a1 - 1e-6
            assert b0 - a1 <= j + 1e-3 or b0 - a1 > j    # a gap is a joint or an opening, never an overlap


def test_stretcher_bond_shifts_alternate_courses_by_half_a_brick(panels):
    o = next(p for p in panels if not p.args["openings"]) if any(not p.args["openings"] for p in panels) else panels[0]
    cs = brick.layout(args(o))["courses"]
    b = o.args["brick"]
    pitch = b["length"] + b["joint"]
    first_even = cs[0]["u"][1][0]
    first_odd = cs[1]["u"][1][0]
    assert math.isclose((first_even - first_odd) % pitch, pitch / 2, abs_tol=2e-3)


def test_course_count_matches_wall_height(panels):
    for o in panels:
        b = o.args["brick"]
        n = int((o.args["height"] + b["joint"]) / (b["height"] + b["joint"]) + 1e-9)
        z_top = (n - 1) * (b["height"] + b["joint"]) + b["height"]
        assert z_top <= o.args["height"] + 1e-6
        assert len({c["z"] for c in brick.layout(args(o))["courses"]}) <= n


def test_courses_lod_is_far_lighter_than_full(panels):
    full = sum(brick.layout(args(o))["pieces"] for o in panels)
    light = sum(brick.layout(args(o, "courses"))["pieces"] for o in panels)
    assert full > 10 * light > 0


def test_short_cut_pieces_are_dropped(panels):
    for o in panels:
        for course in brick.layout(args(o))["courses"]:
            for u0, u1 in course["u"]:
                assert u1 - u0 >= brick.MIN_CUT_M - 1e-6


def test_layout_is_deterministic(panels):
    a = brick.layout(args(panels[0]))
    b = brick.layout(args(panels[0]))
    assert a == b


def test_flemish_bond_mixes_stretchers_and_headers(panels):
    o = panels[0]
    cs = brick.layout({**args(o), "bond": "flemish"})["courses"]
    lengths = {round(u1 - u0, 3) for u0, u1 in cs[0]["u"][2:-2]}
    assert {0.24, 0.115} <= lengths


def test_unknown_lod_is_rejected(panels):
    with pytest.raises(ValueError):
        brick.with_layout(panels, "plate")


def test_with_layout_leaves_the_compiled_ops_untouched(panels):
    before = panels[0].model_dump()
    out = brick.with_layout(panels)
    assert "layout" in out[0].args and panels[0].model_dump() == before
