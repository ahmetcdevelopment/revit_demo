"""Session facade (what the MCP tools call): workflow, offline behaviour and error hints."""

import pytest

from brain.service import Session
from tests.fake_revit import FakeRevit

REAL = "karatay-buyuksinan-1495-26"


@pytest.fixture
def session(tmp_path):
    return Session(out_dir=tmp_path, backend=FakeRevit(online=False))


@pytest.fixture
def online(tmp_path):
    fake = FakeRevit(online=True)
    return Session(out_dir=tmp_path, backend=fake), fake


def test_list_inputs_names_real_and_synthetic_parcels(session):
    r = session.list_inputs()
    assert REAL in r["parcels"] and "demo" in r["zonings"]


def test_load_parcel_reports_edge_roles(session):
    r = session.load_parcel(REAL)
    roles = {e["role"] for e in r["parcel"]["edges"]}
    assert r["ok"] and {"front", "side_party"} <= roles
    assert abs(r["parcel"]["area_computed_m2"] - 1223.42) < 0.05


def test_unknown_parcel_lists_the_valid_names(session):
    r = session.load_parcel("istanbul-1-1")
    assert not r["ok"] and REAL in r["error"] and "list_inputs" in r["hint"]


def test_tools_in_wrong_order_say_what_to_call_first(session):
    assert "load_parcel" in session.check_zoning()["hint"]
    assert "load_parcel" in session.plan_building()["hint"]
    session.load_parcel(REAL)
    assert "plan_building" in session.verify_model()["hint"]
    assert "plan_building" in session.build_in_revit()["hint"]


def test_check_zoning_marks_demo_values_as_assumed(session):
    session.load_parcel(REAL)
    r = session.check_zoning("demo")
    assert r["ok"] and r["report"]["demo_assumption"] is True and r["assumptions"]


def test_unknown_zoning_is_reported(session):
    session.load_parcel(REAL)
    r = session.check_zoning("konya-2030")
    assert not r["ok"] and "demo" in r["error"]


def test_plan_building_writes_spec_and_ops(session, tmp_path):
    session.load_parcel(REAL)
    r = session.plan_building()
    assert r["ok"] and r["validation"]["ok"] and r["ops"] == 595
    assert (tmp_path / "spec.json").exists() and (tmp_path / "ops.json").exists()
    assert 0.35 < r["derived"]["taks"] <= 0.40


def test_planning_failure_is_an_answer_not_a_crash(session):
    session.load_parcel("synthetic_12x25")
    r = session.plan_building(floors=3)
    assert not r["ok"] and "hint" in r and "planning failed" in r["error"]


def test_offline_dry_run_compiles_without_revit(session):
    session.load_parcel(REAL)
    session.plan_building()
    r = session.build_in_revit(dry_run=True)
    assert r["ok"] and r["mode"] == "offline_dry_run" and r["ops"] == 595 and r["ops_by_type"]["create_wall"] == 204


def test_applying_without_revit_explains_how_to_start_it(session):
    session.load_parcel(REAL)
    session.plan_building()
    r = session.build_in_revit(dry_run=False)
    assert not r["ok"] and "Revit" in r["hint"]


def test_get_status_offline_is_not_an_error(session):
    r = session.get_status()
    assert r["ok"] and r["revit"] == "unavailable"


def test_online_flow_applies_only_supported_ops_and_verifies(online):
    s, fake = online
    s.load_parcel(REAL)
    s.plan_building()
    fake.spec = s.spec
    r = s.build_in_revit(dry_run=False, new_project=True)
    assert r["ok"] and r["mode"] == "applied" and r["skipped_ops"] == []
    assert fake.project and fake.project.endswith(f"{REAL}.rvt")
    sent = fake.applied[-1]
    assert {"create_brick_panel", "tag_room"} <= {o["op"] for o in sent["ops"]} and sent["dry_run"] is False
    v = s.verify_model()
    assert v["ok"] and v["differences"] == []


def test_verify_reports_what_is_wrong_in_the_model(online):
    s, fake = online
    s.load_parcel(REAL)
    s.plan_building()
    fake.spec = s.spec
    fake.spec = s.spec.model_copy(update={"rooms": s.spec.rooms[:-1]})   # the model lacks a room
    v = s.verify_model()
    assert not v["ok"] and any("room" in d for d in v["differences"])


def test_export_ifc_writes_a_file(session, tmp_path):
    session.load_parcel(REAL)
    session.plan_building()
    r = session.export_ifc("x.ifc")
    assert r["ok"] and (tmp_path / "x.ifc").stat().st_size > 10_000 and "fallback" in r["route"]
    assert r["consistency"]["ok"] and not r["ids"]["ok"] and r["ids"]["failed"]   # fallback IFC lacks Pset_*Common: said so


def test_export_ifc_cannot_escape_the_out_directory(session, tmp_path):
    session.load_parcel(REAL)
    session.plan_building()
    r = session.export_ifc("../../evil.ifc")
    assert r["ok"] and (tmp_path / "evil.ifc").exists()


def test_dry_run_without_an_open_project_falls_back_to_compiling(tmp_path):
    from brain.backends.revit import RevitBridgeError

    class NoProject(FakeRevit):
        def call(self, method, **params):
            if method == "apply_ops":
                raise RevitBridgeError("no_document", "no active document")
            return super().call(method, **params)

    s = Session(out_dir=tmp_path, backend=NoProject(online=True))
    s.load_parcel(REAL)
    s.plan_building()
    r = s.build_in_revit(dry_run=True)
    assert r["ok"] and r["mode"] == "offline_dry_run" and "no project is open" in r["note"]
    applied = s.build_in_revit(dry_run=False)
    assert not applied["ok"] and "new_project=true" in applied["hint"]
