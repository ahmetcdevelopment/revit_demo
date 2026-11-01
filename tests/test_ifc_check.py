"""compare_ifc on the spec-generated IFC (no Revit): counts must agree and a tampered spec must disagree."""

import pytest

from brain.backends.ifc import IfcBackend
from brain.ifc_check import compare_ifc, ifc_summary
from tests.test_planner import parcel, spec, zoning  # noqa: F401


@pytest.fixture
def ifc_path(spec, tmp_path):
    p = tmp_path / "m.ifc"
    IfcBackend().write(spec, p)
    return p


def test_fallback_ifc_matches_the_spec_counts(spec, ifc_path):
    r = compare_ifc(spec, ifc_path)
    assert r["ok"], r["differences"]
    assert r["summary"]["schema"] == "IFC4" and r["summary"]["storeys"] == len(spec.levels)


def test_a_spec_with_more_rooms_than_the_ifc_is_flagged(spec, ifc_path):
    other = spec.model_copy(update={"rooms": spec.rooms + spec.rooms[:3]})
    r = compare_ifc(other, ifc_path)
    assert not r["ok"] and any(d.startswith("IfcSpace") for d in r["differences"])


def test_summary_reports_no_area_when_the_ifc_has_no_quantities(ifc_path):
    s = ifc_summary(ifc_path)
    assert s["spaces"] > 0 and (s["space_net_area_m2"] is None or s["spaces_with_area"] == s["spaces"])
