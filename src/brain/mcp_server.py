"""MCP server (stdio): the tool surface Claude uses to go from a parcel to a verified Revit model.

Run:  uv run python tools/mcp_server.py   (the launcher puts src/ on the path)
Register with Claude Code:  claude mcp add revit-demo -- uv run --directory <repo> python tools/mcp_server.py
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from .service import Session

INSTRUCTIONS = """\
Parcel -> zoning check -> planned 3-storey bitisik nizam apartment -> built and verified in Revit 2027.
Typical order: list_inputs, load_parcel, check_zoning, plan_building, build_in_revit(dry_run=true),
build_in_revit(dry_run=false, new_project=true), verify_model, export_views, export_ifc, generate_report.
Geometry is produced by a deterministic compiler, not by you: describe intent through the tool arguments
(floors, floor height) and read the results. Zoning values marked 'assumed' are labelled demo assumptions,
not the parcel's real imar durumu; always say so when you report a verdict.
Every tool returns {"ok": ..}; when ok is false read 'error' and 'hint'. build_in_revit is atomic: a
failure rolls the whole Revit model back."""


def create_server(session: Session | None = None) -> MCPServer:
    s = session or Session()
    server = MCPServer("revit-demo", instructions=INSTRUCTIONS)

    @server.tool()
    def list_inputs() -> dict[str, Any]:
        """List the parcels and zoning parameter sets available (names for load_parcel / check_zoning)."""
        return s.list_inputs()

    @server.tool()
    def load_parcel(name: str) -> dict[str, Any]:
        """Load a parcel by name: polygon area, edges with their roles (front/road, party wall neighbour, free)."""
        return s.load_parcel(name)

    @server.tool()
    def check_zoning(zoning: str = "demo") -> dict[str, Any]:
        """Check the loaded parcel against zoning parameters: setbacks, buildable area, TAKS/KAKS limits.
        Each check is pass, fail, warn or assumed (assumed = value is not a verified source)."""
        return s.check_zoning(zoning)

    @server.tool()
    def plan_building(floors: int = 3, floor_height_m: float = 3.0, zoning: str = "demo") -> dict[str, Any]:
        """Plan the building on the loaded parcel (blocks, flats, stairs, openings), validate it against
        zoning and the building rules, and compile the Revit operation list. Returns the spec id,
        TAKS/KAKS, counts and any validation errors."""
        return s.plan_building(floors, floor_height_m, zoning)

    @server.tool()
    def validate_spec() -> dict[str, Any]:
        """Re-run all validation on the planned building (rooms, stairs, access, zoning, PAIY rules)."""
        return s.validate_spec()

    @server.tool()
    def build_in_revit(dry_run: bool = True, new_project: bool = False, prune: bool = False,
                       facade_lod: str = "full") -> dict[str, Any]:
        """Build the planned building in the open Revit project. dry_run=true checks without changing the
        model (works without Revit: it only compiles). new_project=true creates a fresh project first.
        Applying the same plan twice changes nothing (idempotent); prune=true also deletes bridge-made
        elements that are no longer in the plan. facade_lod: "full" models every klinker brick (about 42,000,
        builds in seconds); "courses" models one strip per brick course (about 17 times lighter)."""
        return s.build_in_revit(dry_run, new_project, prune, facade_lod)

    @server.tool()
    def verify_model() -> dict[str, Any]:
        """Read the Revit model back and compare it with the plan: counts, wall lengths, slab and room
        areas, stair risers/treads. ok=false lists each difference by element id."""
        return s.verify_model()

    @server.tool()
    def export_views() -> dict[str, Any]:
        """Export the Revit 3D view and every floor plan as PNG files (paths returned)."""
        return s.export_views()

    @server.tool()
    def export_ifc(filename: str = "", route: str = "auto") -> dict[str, Any]:
        """Export IFC4: from Revit's own exporter when Revit is connected (route auto or revit), otherwise generated
        from the plan (route spec). The file is checked against the project IDS and compared with the plan."""
        return s.export_ifc(filename or None, route)

    @server.tool()
    def generate_report() -> dict[str, Any]:
        """Write one self-contained HTML report (out/project-report.html): parcel and zoning, plan, Revit screenshots,
        spec-Revit-IFC comparison, verification, IDS result and limits. With Revit connected it refreshes every
        measurement first; offline it says which sections are missing."""
        return s.generate_report()

    @server.tool()
    def export_viewer() -> dict[str, Any]:
        """Build the interactive 3D viewer (out/viewer) from the Revit IFC (or the plan IFC): orbit, storeys, element
        groups, section slider, click an element for its IFC info, parcel and setback lines. Open it with
        `uv run python tools/view.py`."""
        return s.export_viewer()

    @server.tool()
    def get_status() -> dict[str, Any]:
        """Revit connection state (version, open project, implemented ops) or 'unavailable' with a hint."""
        return s.get_status()

    return server


def main() -> None:
    create_server().run("stdio")


if __name__ == "__main__":
    main()
