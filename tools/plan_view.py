"""Write out/plan_<level>.html: a full-page floor-plan view of out/spec.json."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from brain.plan_svg import plan_svg
from brain.schemas import BuildingSpec

level = sys.argv[1] if len(sys.argv) > 1 else "L1"
spec = BuildingSpec.model_validate_json((ROOT / "out/spec.json").read_text(encoding="utf-8"))
svg = plan_svg(spec, level).replace("<svg ", '<svg style="width:100%;height:96vh" ', 1)
(ROOT / f"out/plan_{level}.html").write_text(
    f'<body style="margin:0;background:#fff">{svg}</body>', encoding="utf-8")
print(f"out/plan_{level}.html")
