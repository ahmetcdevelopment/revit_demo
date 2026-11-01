"""Builds the real-parcel spec in the running Revit and verifies the model against the spec.

usage: uv run python tools/build_in_revit.py [--new-project] [--dry-run]
Same path as the MCP tools (brain.service.Session); prints the verify_model report.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from brain.service import Session


def main() -> int:
    args = sys.argv[1:]
    s = Session()
    for step, call in (
        ("load_parcel", lambda: s.load_parcel("karatay-buyuksinan-1495-26")),
        ("check_zoning", lambda: s.check_zoning("demo")),
        ("plan_building", lambda: s.plan_building()),
        ("build_in_revit", lambda: s.build_in_revit(dry_run="--dry-run" in args, new_project="--new-project" in args)),
    ):
        r = call()
        print(f"[{step}]", json.dumps({k: v for k, v in r.items() if k not in ("report", "validation")},
                                      ensure_ascii=False)[:600])
        if not r["ok"]:
            return 3
    if "--dry-run" in args:
        return 0
    v = s.verify_model()
    for row in v["rows"]:
        print(f"  {'ok ' if row['ok'] else 'BAD'} {row['category']:<14} spec {row['expected']:<10} model {row['actual']}")
    print(f"verify_model: {'OK' if v['ok'] else 'DIFFERENCES'} ({len(v['differences'])}); "
          f"Revit warnings: {v.get('revit_warnings')}")
    for d in v["differences"][:30]:
        print("  -", d)
    return 0 if v["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
