import pytest

from brain.rules import load_rules
from brain.zoning import check_zoning

RULES = load_rules("data/rules/paiy-2017.yaml")


def test_catalogue_loads_and_every_rule_is_cited():
    assert len(RULES) > 25
    assert all(r.article.startswith("Madde") for r in RULES.values())


def test_paiy_madde23_defaults_match_official_text():
    assert RULES["PAIY-M23-ON"].value == 5.0
    assert RULES["PAIY-M23-YAN"].value == 3.0
    assert RULES["PAIY-M23-ARKA"].value == 3.0
    assert all(RULES[k].overridable_by_plan for k in ("PAIY-M23-ON", "PAIY-M23-YAN"))


@pytest.mark.parametrize("rid,val,ok", [
    ("PAIY-M31-KOL", 1.20, True), ("PAIY-M31-KOL", 1.10, False),
    ("PAIY-M31-2AB", 62.0, True), ("PAIY-M31-2AB", 65.0, False),
    ("PAIY-M29-YATAK-ALAN", 9.0, True), ("PAIY-M29-YATAK-ALAN", 8.9, False),
    ("PAIY-M28-KAT-YUKSEKLIK", 3.0, True), ("PAIY-M28-KAT-YUKSEKLIK", 4.1, False),
])
def test_rule_conditions(rid, val, ok):
    assert RULES[rid].holds(val) is ok


def test_setback_defaults_pass_when_plan_meets_paiy(rect, params):
    r = check_zoning(rect, params, rules=RULES)
    st = {c.id: c.status for c in r.checks}
    assert st["Z-PAIY-M23-ON"] == st["Z-PAIY-M23-YAN"] == st["Z-PAIY-M23-ARKA"] == "pass"


def test_lower_plan_setback_is_a_warning_not_a_failure(rect, params):
    sb = params.setbacks.model_copy(update={"front": 3.0})
    p = type(params).model_validate({**params.model_dump(), "setbacks": sb.model_dump()})
    r = check_zoning(rect, p, rules=RULES)
    c = next(c for c in r.checks if c.id == "Z-PAIY-M23-ON")
    assert c.status == "warn" and r.verdict == "pass"


def test_floor_height_rule_in_report(rect, params):
    r = check_zoning(rect, params, floors=3, floor_height_m=3.0, rules=RULES)
    assert any(c.id == "Z-PAIY-M28-KAT-YUKSEKLIK" and c.status == "pass" for c in r.checks)
