"""The final report: sections present, nothing invented when Revit/IFC were not measured."""

import pytest

from brain.project_report import three_way
from brain.service import Session
from tests.fake_revit import FakeRevit, model_from_spec

REAL = "karatay-buyuksinan-1495-26"


@pytest.fixture
def offline(tmp_path):
    s = Session(out_dir=tmp_path, backend=FakeRevit(online=False))
    s.load_parcel(REAL)
    s.plan_building()
    return s


def test_offline_report_says_what_was_not_measured(offline, tmp_path):
    r = offline.generate_report()
    html = (tmp_path / "project-report.html").read_text(encoding="utf-8")
    assert r["ok"] and not r["has_revit_data"] and not r["has_ifc"]
    assert "DEMO VARSAYIMI" in html and "Revit görüntüsü yok" in html
    assert "Model doğrulaması çalışmadı" in html and "IFC üretilmedi" in html
    assert "okunamadı" in html and "EK-5/EK-6" in html           # the regulation limit is stated, not hidden


def test_offline_report_still_has_zoning_and_plan(offline, tmp_path):
    offline.generate_report()
    html = (tmp_path / "project-report.html").read_text(encoding="utf-8")
    assert "Z-TAKS" in html and "<svg" in html and "VARSAYIM" in html


def test_three_way_uses_none_for_unmeasured_not_zero(offline):
    rows = three_way(offline.spec, None, None)
    assert all(r["revit"] is None and r["ifc"] is None for r in rows)
    assert next(r for r in rows if r["item"] == "Duvar")["spec"] == 204


def test_three_way_with_a_faithful_model_matches_the_spec(offline):
    model = model_from_spec(offline.spec, "full")
    rows = {r["item"]: r for r in three_way(offline.spec, model, None)}
    assert rows["Duvar"]["revit"] == rows["Duvar"]["spec"] == 204
    assert rows["Mahal (oda)"]["revit"] == 102 and rows["Pencere"]["revit"] == 68
    assert rows["Klinker tuğla (adet)"]["revit"] > 30000


def test_online_report_embeds_measurements(tmp_path):
    fake = FakeRevit(online=True)
    s = Session(out_dir=tmp_path, backend=fake)
    s.load_parcel(REAL)
    s.plan_building()
    fake.spec = s.spec
    s.build_in_revit(dry_run=False)
    r = s.generate_report()
    html = (tmp_path / "project-report.html").read_text(encoding="utf-8")
    assert r["has_revit_data"] and "MODEL = SPEC" in html and "Üç yönlü" in html
