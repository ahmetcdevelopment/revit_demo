"""Session facade behind the MCP tools: every method returns a plain JSON-able dict.

The session remembers the current parcel, zoning parameters and spec between calls (the MCP server is one
long-lived process). Failures come back as {"ok": False, "error": ..., "hint": ...} so a language model
can read them and recover, instead of a stack trace.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from .backends import IfcBackend
from .backends.revit import BridgeUnavailable, RevitBackend, RevitBridgeError
from .catalog import (
    OUT_DIR,
    CatalogError,
    list_parcels,
    list_zonings,
    load_default_rules,
    load_parcel,
    load_zoning_params,
)
from .brick import LODS, expected_pieces as brick_expected, with_layout
from .brick import stats as brick_layout_stats
from .compiler import compile_spec
from .ifc_check import compare_ifc
from .project_report import render_project_report
from .viewer_export import export_viewer
from .ids_profile import check_ifc
from .planner import PlanningError, plan_building
from .schemas import BuildingSpec, ParcelSpec, ZoningParams
from .validate import validate_spec
from .verify import verify
from .zoning import check_zoning


class SessionError(Exception):
    def __init__(self, message: str, hint: str):
        super().__init__(message)
        self.message, self.hint = message, hint


def guarded(fn: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    """Turn expected failures into {"ok": False, error, hint}."""

    def wrapper(*a: Any, **kw: Any) -> dict[str, Any]:
        try:
            return fn(*a, **kw)
        except SessionError as e:
            return {"ok": False, "error": e.message, "hint": e.hint}
        except CatalogError as e:
            return {"ok": False, "error": str(e), "hint": "use list_inputs to see valid names"}
        except PlanningError as e:
            return {"ok": False, "error": f"planning failed: {e}",
                    "hint": "the parcel cannot hold the building with these zoning parameters; "
                            "check check_zoning (buildable area) or try fewer floors"}
        except BridgeUnavailable as e:
            return {"ok": False, "error": f"Revit bridge not reachable: {e}",
                    "hint": "start Revit 2027 with the RevitBridge add-in loaded, then call get_status"}
        except RevitBridgeError as e:
            hints = {
                "no_document": "call build_in_revit with new_project=true to create the project first",
                "missing_ref": "an element the op depends on is not in the model; rebuild with prune=false "
                               "from a new project",
                "unsupported_op": "the add-in does not implement this op yet",
            }
            return {"ok": False, "error": str(e), "code": e.code, "op_id": e.op_id,
                    "hint": hints.get(e.code, "the model was rolled back; nothing was half-applied"),
                    "rolled_back": True}

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


class Session:
    def __init__(self, out_dir: Path | None = None, backend: RevitBackend | None = None):
        self.out = out_dir or OUT_DIR
        self.backend = backend or RevitBackend()
        self.rules = load_default_rules()
        self.parcel: ParcelSpec | None = None
        self.zoning: ZoningParams | None = None
        self.spec: BuildingSpec | None = None
        self.validation: Any = None
        self.lod = "full"
        self._model: dict[str, Any] | None = None
        self._verify: dict[str, Any] | None = None
        self._ifc: dict[str, Any] | None = None
        self._ids: dict[str, Any] | None = None
        self._zoning_report: Any = None

    # ---------------------------------------------------------------- inputs
    @guarded
    def list_inputs(self) -> dict[str, Any]:
        return {"ok": True, "parcels": list_parcels(), "zonings": list_zonings(),
                "note": "parcels are frozen TKGM / manual fixtures; zonings marked demo_assumption are "
                        "labelled assumptions, not the parcel's real imar durumu"}

    @guarded
    def load_parcel(self, name: str) -> dict[str, Any]:
        p = load_parcel(name)
        self.parcel, self.spec = p, None
        return {"ok": True, "parcel": self._parcel_summary(p)}

    @staticmethod
    def _parcel_summary(p: ParcelSpec) -> dict[str, Any]:
        return {
            "parcel_id": p.parcel_id, "source": p.source.type,
            "area_computed_m2": round(p.area_computed_m2, 2), "area_tapu_m2": p.area_tapu_m2,
            "edges": [{"i": e.i, "length_m": round(e.length, 2), "role": e.role.value,
                       "adjacent": e.adjacent.value} for e in p.edges],
        }

    def _need_parcel(self) -> ParcelSpec:
        if self.parcel is None:
            raise SessionError("no parcel loaded", "call load_parcel first (list_inputs shows the names)")
        return self.parcel

    def _need_spec(self) -> BuildingSpec:
        if self.spec is None:
            raise SessionError("no building planned yet", "call plan_building first")
        return self.spec

    # ---------------------------------------------------------------- zoning / planning
    @guarded
    def check_zoning(self, zoning: str = "demo") -> dict[str, Any]:
        parcel = self._need_parcel()
        self.zoning = load_zoning_params(zoning)
        rep = check_zoning(parcel, self.zoning, rules=self.rules)
        self._zoning_report = rep
        return {"ok": True, "zoning": zoning, "report": rep.model_dump(mode="json"),
                "assumptions": [c.id for c in rep.checks if c.status == "assumed"]}

    @guarded
    def plan_building(self, floors: int = 3, floor_height_m: float = 3.0, zoning: str = "demo") -> dict[str, Any]:
        parcel = self._need_parcel()
        if self.zoning is None or zoning != "demo":
            self.zoning = load_zoning_params(zoning)
        self.spec = plan_building(parcel, self.zoning, floors=floors, floor_height=floor_height_m)
        res = validate_spec(self.spec, parcel=parcel, params=self.zoning, rules=self.rules)
        self.validation = res
        ops = compile_spec(self.spec)
        self.out.mkdir(exist_ok=True)
        (self.out / "spec.json").write_text(self.spec.model_dump_json(indent=2), encoding="utf-8")
        (self.out / "ops.json").write_text(
            json.dumps([o.model_dump() for o in ops], indent=1, ensure_ascii=False), encoding="utf-8")
        return {"ok": True, "spec_id": self.spec.spec_id, "ops": len(ops),
                "derived": self.spec.derived.model_dump(mode="json"),
                "counts": {"blocks": len(self.spec.blocks), "walls": len(self.spec.walls),
                           "rooms": len(self.spec.rooms), "openings": len(self.spec.openings),
                           "stairs": len(self.spec.stairs)},
                "validation": self._validation_summary(res), "known_gaps": self.spec.known_gaps}

    @staticmethod
    def _validation_summary(res: Any) -> dict[str, Any]:
        return {"ok": res.ok, "zoning_verdict": res.zoning.verdict if res.zoning else None,
                "errors": [i.model_dump(mode="json") for i in res.errors()],
                "warnings": [i.model_dump(mode="json") for i in res.issues if i.level == "warn"]}

    @guarded
    def validate_spec(self) -> dict[str, Any]:
        spec, parcel = self._need_spec(), self._need_parcel()
        res = self.validation = validate_spec(spec, parcel=parcel, params=self.zoning, rules=self.rules)
        return {"ok": True, "spec_id": spec.spec_id, **self._validation_summary(res)}

    # ---------------------------------------------------------------- Revit
    def _connected(self) -> bool:
        try:
            self.backend.ping()
            return True
        except BridgeUnavailable:
            return False

    @guarded
    def get_status(self) -> dict[str, Any]:
        if not self._connected():
            return {"ok": True, "revit": "unavailable",
                    "hint": "start Revit 2027 with the RevitBridge add-in; offline work (zoning, planning, "
                            "dry-run, IFC) still works"}
        ping, status = self.backend.ping(), self.backend.status()
        return {"ok": True, "revit": "connected", "ops": ping["ops"], "ops_version": ping.get("ops_version"),
                "status": status}

    @guarded
    def build_in_revit(self, dry_run: bool = True, new_project: bool = False, prune: bool = False,
                       facade_lod: str = "full") -> dict[str, Any]:
        spec = self._need_spec()
        if self.validation is not None and not self.validation.ok:
            errors = self.validation.errors()
            return {"ok": False, "blocked": True, "spec_id": spec.spec_id,
                    "error": f"the plan has {len(errors)} validation error(s); nothing was sent to Revit",
                    "errors": [i.model_dump(mode="json") for i in errors[:10]],
                    "hint": "a plan that fails zoning or building rules is never built; change the inputs "
                            "(floors, floor height) and call plan_building again"}
        if facade_lod not in LODS:
            raise SessionError(f"facade_lod '{facade_lod}' is not valid", f"use one of: {', '.join(LODS)}")
        ops = compile_spec(spec)
        by_op = dict(Counter(o.op for o in ops))
        self.lod = facade_lod
        brick_stats = brick_layout_stats(ops, facade_lod)
        if not self._connected():
            if dry_run:
                return {"ok": True, "mode": "offline_dry_run", "spec_id": spec.spec_id, "ops": len(ops),
                        "ops_by_type": by_op, "klinker": brick_stats,
                        "note": "Revit is not running: the op list compiled, nothing was checked in Revit"}
            raise BridgeUnavailable("endpoint.json not found")
        project = None
        if new_project and not dry_run:
            project = self.backend.new_project((self.out / f"{spec.project.parcel_id}.rvt").resolve())
        try:
            result, skipped = self.backend.apply_supported(with_layout(ops, facade_lod), spec.spec_id,
                                                           dry_run=dry_run, prune=prune)
        except RevitBridgeError as e:
            if dry_run and e.code == "no_document":
                return {"ok": True, "mode": "offline_dry_run", "spec_id": spec.spec_id, "ops": len(ops),
                        "ops_by_type": by_op, "klinker": brick_stats,
                        "note": "Revit is running but no project is open: the op list compiled; "
                                "use new_project=true with dry_run=false to create one"}
            raise
        shown = None
        if not dry_run:
            try:
                shown = self.backend.show_3d()["view"]    # the person should see the building, not a floor plan
            except (RevitBridgeError, BridgeUnavailable):
                shown = None
        return {"ok": True, "mode": "dry_run" if dry_run else "applied", "spec_id": spec.spec_id, "showing_view": shown,
                "created": result["created"], "updated": result["updated"], "unchanged": result["unchanged"],
                "deleted": result.get("deleted", 0), "ops_by_type": by_op, "skipped_ops": skipped,
                "klinker": brick_stats, "project": project, "revit_messages": result["warnings"][:20]}

    @guarded
    def verify_model(self) -> dict[str, Any]:
        spec = self._need_spec()
        expected = brick_expected(compile_spec(spec), self.lod)
        self._model = self.backend.read_back()
        report = verify(spec, self._model, brick_expected=expected)
        self._verify = report.model_dump(mode="json")
        return {"ok": report.ok, **report.model_dump(mode="json")}

    @guarded
    def export_views(self) -> dict[str, Any]:
        out = self.backend.export_views(self.out / "revit-views")
        return {"ok": True, **out}

    # ---------------------------------------------------------------- IFC
    @guarded
    def export_ifc(self, filename: str | None = None, route: str = "auto") -> dict[str, Any]:
        """IFC4 from Revit's own exporter when Revit is connected (route auto/revit), else generated from the
        spec with IfcOpenShell. Either way the IFC is checked against the project IDS and compared with the spec."""
        spec = self._need_spec()
        if route not in ("auto", "revit", "spec"):
            raise SessionError(f"route '{route}' is not valid", "use auto, revit or spec")
        use_revit = route != "spec" and self._connected()
        if route == "revit" and not use_revit:
            raise BridgeUnavailable("endpoint.json not found")
        self.out.mkdir(exist_ok=True)
        name = Path(filename).name if filename else ("revit.ifc" if use_revit else "model.ifc")
        path = self.out / name
        if use_revit:
            self.backend.export_ifc(self.out, name, project_name=spec.project.name,
                                    building_name=f"{spec.project.parcel_id} Blok A+B",
                                    address=spec.project.parcel_id)
            label = "Revit IFC4 exporter"
        else:
            IfcBackend().write(spec, path)
            label = "ifcopenshell fallback (generated from the spec, not from Revit)"
        ids_res = check_ifc(path, html_out=self.out / f"ids-{path.stem}.html")
        cons = compare_ifc(spec, path)
        failed = [s["name"] for s in ids_res["specifications"] if not s["status"]]
        self._ifc = {"route": label, "bytes": path.stat().st_size, "summary": cons["summary"]}
        self._ids = {"ok": ids_res["ok"], "specifications": len(ids_res["specifications"]), "failed": failed,
                     "profile": ids_res["profile"]}
        return {"ok": True, "path": str(path), "bytes": path.stat().st_size, "route": label,
                "ids": {"ok": ids_res["ok"], "specifications": len(ids_res["specifications"]),
                        "failed": failed, "profile": ids_res["profile"],
                        "report": str(self.out / f"ids-{path.stem}.html")},
                "consistency": {"ok": cons["ok"], "rows": cons["rows"], "differences": cons["differences"]},
                "klinker_in_ifc": cons["summary"]["brick_panels"]}

    # ---------------------------------------------------------------- report
    @guarded
    def generate_report(self, refresh: bool = True) -> dict[str, Any]:
        """One self-contained HTML report. With Revit connected (and refresh) it first re-reads the model, verifies it,
        exports the views and the IFC so every number in the report is current; offline it uses what was measured
        earlier in this session and says what is missing."""
        spec, parcel = self._need_spec(), self._need_parcel()
        if self.zoning is None:
            self.check_zoning()
        # the report shows the checks of THIS plan (TAKS, KAKS, height, setback fit), not just the parcel
        self._zoning_report = check_zoning(
            parcel, self.zoning, footprints=spec.footprints, floors=len(spec.levels) - 1,
            floor_height_m=spec.levels[0].height, rules=self.rules)
        measured: list[str] = []
        if refresh and self._connected():
            try:
                self.verify_model()
                self.export_views()
                self.export_ifc()
                measured = ["revit read-back", "views", "ifc", "ids"]
            except RevitBridgeError:
                measured = []   # e.g. no open project: the report states what is missing
        scenario = self.out / "test-report.md"
        html = render_project_report(
            parcel=parcel, params=self.zoning, zoning=self._zoning_report, spec=spec, validation=self.validation,
            verify_report=self._verify, model=self._model, ifc=self._ifc, ids=self._ids,
            views_dir=self.out / "revit-views", lod=self.lod,
            scenario_md=scenario.read_text(encoding="utf-8") if scenario.exists() else None)
        path = self.out / "project-report.html"
        path.write_text(html, encoding="utf-8")
        return {"ok": True, "path": str(path), "bytes": path.stat().st_size, "measured_now": measured,
                "has_revit_data": self._model is not None, "has_ifc": self._ifc is not None}

    # ---------------------------------------------------------------- browser viewer
    @guarded
    def export_viewer(self, ifc: str | None = None) -> dict[str, Any]:
        """Folder out/viewer: an interactive 3D model (orbit, storeys, element groups, section, click for info) built
        from an IFC file. Uses the Revit IFC when it exists (or exports one when Revit is connected), else the spec IFC."""
        spec, parcel = self._need_spec(), self._need_parcel()
        if self._zoning_report is None:
            self.check_zoning()
        self.out.mkdir(exist_ok=True)
        path = Path(ifc) if ifc else None
        if path is None:
            revit_ifc = self.out / "revit.ifc"
            if self._connected() and not revit_ifc.exists():
                self.export_ifc()
            path = revit_ifc if revit_ifc.exists() else self.out / "model.ifc"
            if not path.exists():
                IfcBackend().write(spec, path)
        d = spec.derived
        area = parcel.area_tapu_m2 or parcel.area_computed_m2
        scene = {
            "title": f"{parcel.parcel_id}",
            "subtitle": f"{spec.project.name} · spec {spec.spec_id} · IFC: {path.name}",
            "demo_assumption": self.zoning.source_doc.type == "demo_assumption" if self.zoning else True,
            "kpis": [{"label": "parsel m²", "value": f"{area:,.0f}"}, {"label": "TAKS", "value": d.taks},
                     {"label": "KAKS", "value": d.kaks}, {"label": "brüt m²", "value": f"{d.gross_area_m2:,.0f}"},
                     {"label": "blok", "value": d.blocks}],
            "parcel": {"ring": [list(p) for p in parcel.ring_local],
                       "edges": [{"a": list(e.a), "b": list(e.b), "role": e.role.value} for e in parcel.edges]},
            "buildable": [list(p) for p in self._zoning_report.buildable_polygon] if self._zoning_report else None,
            "footprints": [[list(p) for p in f] for f in spec.footprints],
        }
        src = Path(__file__).resolve().parents[1] / "viewer"
        info = export_viewer(path, self.out / "viewer", scene, src)
        return {"ok": True, **info, "serve": "uv run python tools/view.py", "ifc": str(path)}
