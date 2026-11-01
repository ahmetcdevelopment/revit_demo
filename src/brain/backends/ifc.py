"""IfcBackend: BuildingSpec -> IFC4 (fallback path, decision D14; no Revit needed).

Geometry is simplified: walls/slabs/spaces are extrusions, openings are voids filled by box
doors/windows, the stair is a placeholder volume. The final deliverable IFC comes from Revit (P6).
"""

from __future__ import annotations

import math
from pathlib import Path

import ifcopenshell
import ifcopenshell.api
import numpy as np
from shapely.geometry import Polygon

from ..schemas import BuildingSpec

api = ifcopenshell.api


def _m(origin: tuple[float, float, float], x_axis: tuple[float, float]) -> np.ndarray:
    """4x4 placement: local x along x_axis (unit), local y = left normal, z up."""
    ax, ay = x_axis
    m = np.eye(4)
    m[:3, 0] = (ax, ay, 0.0)
    m[:3, 1] = (-ay, ax, 0.0)
    m[:3, 3] = origin
    return m


class IfcBackend:
    def build(self, spec: BuildingSpec) -> ifcopenshell.file:
        f = api.run("project.create_file", version="IFC4")
        project = api.run("root.create_entity", f, ifc_class="IfcProject", name=spec.project.name)
        project.Description = f"spec_id={spec.spec_id}"
        api.run("unit.assign_unit", f, length={"is_metric": True, "raw": "METERS"},
                area={"is_metric": True, "raw": "SQUARE_METERS"},
                volume={"is_metric": True, "raw": "CUBIC_METERS"})
        ctx = api.run("context.add_context", f, context_type="Model")
        body = api.run("context.add_context", f, context_type="Model", context_identifier="Body",
                       target_view="MODEL_VIEW", parent=ctx)
        site = api.run("root.create_entity", f, ifc_class="IfcSite", name=spec.project.parcel_id)
        building = api.run("root.create_entity", f, ifc_class="IfcBuilding", name=spec.project.name)
        api.run("aggregate.assign_object", f, products=[site], relating_object=project)
        api.run("aggregate.assign_object", f, products=[building], relating_object=site)

        storeys = {}
        for lv in spec.levels:
            st = api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name=lv.name)
            st.Elevation = lv.elevation
            api.run("aggregate.assign_object", f, products=[st], relating_object=building)
            storeys[lv.id] = st
        elev = {lv.id: lv.elevation for lv in spec.levels}

        def place(el, matrix, rep):
            api.run("geometry.assign_representation", f, product=el, representation=rep)
            api.run("geometry.edit_object_placement", f, product=el, matrix=matrix)

        def extrusion(el, level, polyline, depth, z):
            rep = api.run("geometry.add_slab_representation", f, context=body, depth=depth,
                          polyline=[tuple(p) for p in polyline])
            m = np.eye(4)
            m[2, 3] = z
            place(el, m, rep)
            api.run("spatial.assign_container", f, products=[el], relating_structure=storeys[level])

        walls = {}
        for w in spec.walls:
            wall = api.run("root.create_entity", f, ifc_class="IfcWall", name=w.id)
            dx, dy = w.b[0] - w.a[0], w.b[1] - w.a[1]
            length = math.hypot(dx, dy)
            d = (dx / length, dy / length)
            n = (-d[1], d[0])
            origin = (w.a[0] - n[0] * w.thickness / 2, w.a[1] - n[1] * w.thickness / 2, elev[w.level])
            rep = api.run("geometry.add_wall_representation", f, context=body, length=length,
                          height=w.height, thickness=w.thickness)
            place(wall, _m(origin, d), rep)
            api.run("spatial.assign_container", f, products=[wall], relating_structure=storeys[w.level])
            pset = api.run("pset.add_pset", f, product=wall, name="Pset_WallCommon")
            api.run("pset.edit_pset", f, pset=pset, properties={
                "IsExternal": w.type in ("ext_brick",), "LoadBearing": w.type != "partition"})
            walls[w.id] = (wall, d, n, w.thickness)

        for s in spec.slabs:
            slab = api.run("root.create_entity", f, ifc_class="IfcSlab", name=s.id,
                           predefined_type="FLOOR")
            extrusion(slab, s.level, s.outline, s.thickness, elev[s.level] - s.thickness)
            for i, hole in enumerate(s.openings):
                op = api.run("root.create_entity", f, ifc_class="IfcOpeningElement",
                             name=f"{s.id}-OPEN-{i}")
                rep = api.run("geometry.add_slab_representation", f, context=body,
                              depth=s.thickness + 0.2, polyline=[tuple(p) for p in hole])
                m = np.eye(4)
                m[2, 3] = elev[s.level] - s.thickness - 0.1
                place(op, m, rep)
                api.run("feature.add_feature", f, feature=op, element=slab)

        for o in spec.openings:
            wall, d, n, t = walls[o.host_wall]
            cls = "IfcDoor" if o.kind == "door" else "IfcWindow"
            z = elev[o.level] + o.sill
            for kind, name, depth in (("opening", f"{o.id}-VOID", t + 0.1), ("fill", o.id, 0.06)):
                el = api.run("root.create_entity", f, ifc_class="IfcOpeningElement" if kind ==
                             "opening" else cls, name=name)
                rep = api.run("geometry.add_wall_representation", f, context=body, length=o.width,
                              height=o.height, thickness=depth)
                origin = (o.at[0] - d[0] * o.width / 2 - n[0] * depth / 2,
                          o.at[1] - d[1] * o.width / 2 - n[1] * depth / 2, z)
                place(el, _m(origin, d), rep)
                if kind == "opening":
                    api.run("feature.add_feature", f, feature=el, element=wall)
                    opening_el = el
                else:
                    el.OverallWidth, el.OverallHeight = o.width, o.height
                    api.run("spatial.assign_container", f, products=[el],
                            relating_structure=storeys[o.level])
                    api.run("feature.add_filling", f, opening=opening_el, element=el)

        for r in spec.rooms:
            height = next(lv.height for lv in spec.levels if lv.id == r.level)
            space = api.run("root.create_entity", f, ifc_class="IfcSpace", name=r.name)
            space.LongName = r.id
            rep = api.run("geometry.add_slab_representation", f, context=body, depth=height,
                          polyline=[tuple(p) for p in r.outline])
            m = np.eye(4)
            m[2, 3] = elev[r.level]
            place(space, m, rep)
            api.run("aggregate.assign_object", f, products=[space], relating_object=storeys[r.level])
            qto = api.run("pset.add_qto", f, product=space, name="Qto_SpaceBaseQuantities")
            api.run("pset.edit_qto", f, qto=qto, properties={
                "NetFloorArea": round(Polygon(r.outline).area, 4)})

        for st in spec.stairs:
            stair = api.run("root.create_entity", f, ifc_class="IfcStair", name=st.id)
            cw = 2 * st.run_width + st.well_width
            o, dv, sv = st.origin, st.direction, st.side
            poly = [(o[0], o[1]),
                    (o[0] + sv[0] * cw, o[1] + sv[1] * cw),
                    (o[0] + sv[0] * cw + dv[0] * st.zone_length, o[1] + sv[1] * cw + dv[1] * st.zone_length),
                    (o[0] + dv[0] * st.zone_length, o[1] + dv[1] * st.zone_length)]
            poly = list(poly if Polygon(poly).exterior.is_ccw else reversed(poly))
            extrusion(stair, st.from_level, poly, elev[st.to_level] - elev[st.from_level],
                      elev[st.from_level])

        top = spec.levels[-1].id
        for rf in spec.roofs:
            roof = api.run("root.create_entity", f, ifc_class="IfcRoof", name=rf.id,
                           predefined_type="FLAT_ROOF")
            extrusion(roof, top, rf.outline, rf.thickness, elev[top])
        return f

    def write(self, spec: BuildingSpec, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.build(spec).write(str(path))
        return path
