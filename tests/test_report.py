import subprocess
import sys
from pathlib import Path

from brain.report import render_report
from brain.rules import load_rules
from brain.zoning import check_zoning

ROOT = Path(__file__).resolve().parents[1]


def test_report_contains_checks_citations_and_demo_banner(rect, params):
    rules = load_rules("data/rules/paiy-2017.yaml")
    rep = check_zoning(rect, params, footprint=[(0, 5), (20, 5), (20, 17), (0, 17)], floors=3,
                       floor_height_m=3.0, rules=rules)
    html = render_report(rect, rep, params)
    assert "DEMO VARSAYIMI" in html and "<svg" in html
    assert "Z-TAKS" in html and "PAİY Madde 23(1)(a)" in html and "VARSAYIM" in html


def test_cli_builds_report():
    r = subprocess.run([sys.executable, "tools/make_report.py",
                        "data/parcels/synthetic_12x25.manual.json"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (ROOT / "out" / "report.html").exists()
    assert "verdict=pass" in r.stdout
