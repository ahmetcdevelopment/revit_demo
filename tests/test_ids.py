"""The project IDS must be able to fail: a checker that cannot reject anything proves nothing."""

import ifcopenshell
import ifcopenshell.api
import pytest
from ifctester import ids

from brain import ids_profile as P


def minimal_ifc(path, space_names):
    f = ifcopenshell.api.run("project.create_file", version="IFC4")
    project = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcProject", name="p")
    ifcopenshell.api.run("unit.assign_unit", f)
    site = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSite", name="s")
    building = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuilding", name="b")
    storey = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="Zemin")
    ifcopenshell.api.run("aggregate.assign_object", f, products=[site], relating_object=project)
    ifcopenshell.api.run("aggregate.assign_object", f, products=[building], relating_object=site)
    ifcopenshell.api.run("aggregate.assign_object", f, products=[storey], relating_object=building)
    for n in space_names:
        sp = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSpace", name=n)
        sp.LongName = "Salon"
        ifcopenshell.api.run("aggregate.assign_object", f, products=[sp], relating_object=storey)
    f.write(str(path))
    return path


def only_space_numbering() -> ids.Ids:
    my = ids.Ids(title="t")
    P._spec(my, "T", "space numbering", "IFCSPACE", [P.attr("Name", r"L\d-B\d+-.+"), P.attr("LongName")], P.PRACTICE)
    return my


def run(tmp_path, names):
    ifc = minimal_ifc(tmp_path / "m.ifc", names)
    idsfile = tmp_path / "t.ids"
    only_space_numbering().to_xml(str(idsfile))
    return P.check_ifc(ifc, idsfile)


def test_a_conforming_model_passes(tmp_path):
    r = run(tmp_path, ["L0-B1-A-SALON", "L1-B2-B-MUTFAK"])
    assert r["ok"] and r["specifications"][0]["passed"] == 2


def test_one_badly_named_space_is_caught_exactly(tmp_path):
    r = run(tmp_path, ["L0-B1-A-SALON", "Salon", "L2-B1-A-HOL"])
    s = r["specifications"][0]
    assert not r["ok"] and (s["passed"], s["failed"], s["applicable"]) == (2, 1, 3)


def test_missing_entities_fail_a_required_specification(tmp_path):
    r = run(tmp_path, [])
    assert not r["ok"]


def test_the_shipped_profile_has_the_expected_specifications(tmp_path):
    p = P.write_ids(tmp_path / "project.ids")
    spec = ids.open(str(p))
    names = [s.name for s in spec.specifications]
    assert len(names) == 10 and any("numbering" in n for n in names)
    assert all(s.description and s.description.startswith("source:") for s in spec.specifications)
    regulation = [s for s in spec.specifications if "regulation" in s.description]
    assert len(regulation) == 1 and "7(2)" in regulation[0].description   # only what the read text supports


def test_the_committed_ids_file_matches_the_generator(tmp_path):
    fresh = P.write_ids(tmp_path / "fresh.ids").read_text(encoding="utf-8")
    committed = P.IDS_PATH.read_text(encoding="utf-8")
    strip = lambda s: "\n".join(line for line in s.splitlines() if "<date>" not in line)  # noqa: E731
    assert strip(fresh) == strip(committed), "run: uv run python -c 'from brain.ids_profile import write_ids; write_ids()'"


@pytest.mark.skipif(not (P.IDS_PATH.parent.parent.parent / "out" / "model.ifc").exists(), reason="no generated IFC")
def test_the_fallback_ifc_is_reported_as_incomplete_not_hidden():
    r = P.check_ifc(P.IDS_PATH.parent.parent.parent / "out" / "model.ifc")
    assert not r["ok"]      # the spec-generated IFC has no Pset_*Common; the report must say so
