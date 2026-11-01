"""Golden files: any change to the planner/compiler output must be reviewed and re-recorded.

Re-record with:  UPDATE_GOLDEN=1 uv run pytest tests/test_golden.py
"""

import json
import os
from pathlib import Path

from brain.compiler import compile_spec
from tests.test_planner import parcel, spec, zoning  # noqa: F401

GOLDEN = Path(__file__).parent / "golden"


def _check(name: str, text: str) -> None:
    path = GOLDEN / name
    if os.environ.get("UPDATE_GOLDEN"):
        GOLDEN.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    assert path.read_text(encoding="utf-8") == text, f"{name} changed; review, then UPDATE_GOLDEN=1"


def test_spec_golden(spec):
    _check("spec_karatay_1495_26.json", spec.model_dump_json(indent=1) + "\n")


def test_ops_golden(spec):
    ops = [o.model_dump() for o in compile_spec(spec)]
    _check("ops_karatay_1495_26.json", json.dumps(ops, indent=1, ensure_ascii=False) + "\n")


def test_tools_script_end_to_end(tmp_path):
    from tools.plan_demo import run
    s = run(out=tmp_path)
    assert s["ok"] and s["errors"] == [] and s["zoning"] == "pass"
    assert (tmp_path / "model.ifc").stat().st_size > 10_000
