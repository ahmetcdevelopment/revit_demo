"""IFC -> GLB for the browser viewer (src/viewer), plus scene.json with the parcel, the buildable area and the numbers.

One glTF node per IFC product (so a click can say which wall or room it is); klinker panels are single meshes.
Coordinates: IFC is Z-up in metres, glTF is Y-up, so (x, y, z) -> (x, z, -y). Colours come from the IFC styles
(Revit writes them); classes without a usable style get a palette colour.
"""

from __future__ import annotations

import json
import math
import os
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as element
import ifcopenshell.util.unit
import numpy as np


PALETTE = {
    "IfcWall": (0.82, 0.80, 0.74), "IfcSlab": (0.70, 0.70, 0.68), "IfcRoof": (0.45, 0.45, 0.48),
    "IfcDoor": (0.48, 0.33, 0.20), "IfcWindow": (0.62, 0.78, 0.88), "IfcStairFlight": (0.65, 0.62, 0.58),
    "IfcStair": (0.65, 0.62, 0.58), "IfcRailing": (0.30, 0.30, 0.32), "IfcMember": (0.85, 0.85, 0.85),
    "IfcBuildingElementProxy": (0.80, 0.80, 0.80), "IfcSpace": (0.40, 0.65, 0.85),
}
KLINKER = (0.54, 0.23, 0.17)


@dataclass
class Piece:
    name: str
    extras: dict[str, Any]
    prims: list[tuple[int, np.ndarray, np.ndarray]] = field(default_factory=list)   # (material, xyz, triangles)


class Materials:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []
        self.index: dict[tuple[float, ...], int] = {}

    def get(self, rgb: tuple[float, float, float], alpha: float = 1.0) -> int:
        key = tuple(round(c, 3) for c in (*rgb, alpha))
        if key not in self.index:
            self.index[key] = len(self.items)
            self.items.append({
                "pbrMetallicRoughness": {"baseColorFactor": [*key[:3], key[3]], "metallicFactor": 0.0, "roughnessFactor": 0.9},
                "alphaMode": "BLEND" if alpha < 0.99 else "OPAQUE", "doubleSided": True})
        return self.index[key]


def _style_colour(mat: Any) -> tuple[tuple[float, float, float], float] | None:
    try:
        d = mat.diffuse
        rgb = tuple(float(c) for c in (d.components if hasattr(d, "components") else d))[:3]
        t = float(getattr(mat, "transparency", 0.0) or 0.0)
        a = 1.0 - t
        if not all(math.isfinite(c) for c in (*rgb, a)):      # some Revit styles carry NaN transparency
            return None if not all(math.isfinite(c) for c in rgb) else (rgb, 1.0)
        return rgb, max(0.0, min(1.0, a))
    except Exception:  # noqa: BLE001
        return None


def _is_default_grey(rgb: tuple[float, float, float]) -> bool:
    return max(rgb) - min(rgb) < 0.02 and 0.7 < rgb[0] < 0.86


def _storey_of(el: Any) -> str | None:
    c = element.get_container(el)
    while c is not None and not c.is_a("IfcBuildingStorey"):
        c = element.get_container(c)
    return c.Name if c is not None else None


def collect(ifc_path: str | Path, threads: int | None = None) -> tuple[list[Piece], Materials, dict[str, Any]]:
    f = ifcopenshell.open(str(ifc_path))
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    it = ifcopenshell.geom.iterator(settings, f, threads or max(2, (os.cpu_count() or 4) - 1))
    mats = Materials()
    pieces: list[Piece] = []
    counts: dict[str, int] = {}
    if it.initialize():
        while True:
            shape = it.get()
            el = f.by_id(shape.id)
            cls = el.is_a()
            if cls != "IfcOpeningElement":
                gm = shape.geometry
                v = np.asarray(gm.verts, dtype=np.float64).reshape(-1, 3)
                tri = np.asarray(gm.faces, dtype=np.uint32).reshape(-1, 3)
                if len(v) and len(tri):
                    xyz = np.stack([v[:, 0], v[:, 2], -v[:, 1]], axis=1).astype(np.float32)   # Z-up -> Y-up
                    mids = np.asarray(gm.material_ids, dtype=np.int64)
                    is_klinker = cls == "IfcBuildingElementProxy" and (el.Name or "").startswith("BP-")
                    piece = Piece(name=el.Name or cls, extras={
                        "ifc": cls, "guid": el.GlobalId, "name": el.Name, "long_name": getattr(el, "LongName", None),
                        "storey": _storey_of(el), "klinker": is_klinker})
                    groups: dict[int, list[int]] = {}
                    for i, m in enumerate(mids):
                        groups.setdefault(int(m), []).append(i)
                    for m_idx, faces in groups.items():
                        style = _style_colour(gm.materials[m_idx]) if 0 <= m_idx < len(gm.materials) else None
                        rgb, alpha = style if style else (PALETTE.get(cls, (0.8, 0.8, 0.8)), 1.0)
                        if is_klinker:
                            rgb, alpha = KLINKER, 1.0
                        elif cls != "IfcSpace" and _is_default_grey(rgb):
                            rgb = PALETTE.get(cls, rgb)
                        if cls == "IfcSpace":
                            rgb, alpha = PALETTE["IfcSpace"], 0.35
                        if cls == "IfcWindow" and alpha > 0.99 and rgb[2] > rgb[0]:
                            alpha = 0.55
                        piece.prims.append((mats.get(rgb, alpha), xyz, tri[faces]))
                    if piece.prims:
                        pieces.append(piece)
                        counts[cls] = counts.get(cls, 0) + 1
            if not it.next():
                break
    scale = ifcopenshell.util.unit.calculate_unit_scale(f)     # metres per project length unit
    storeys = sorted(((s.Name, float(s.Elevation or 0) * scale)
                      for s in f.by_type("IfcBuildingStorey")), key=lambda t: t[1])
    return pieces, mats, {"counts": counts, "storeys": storeys, "schema": f.schema}


def _pad(b: bytes, fill: bytes = b"\x00") -> bytes:
    return b + fill * (-len(b) % 4)


def build_glb(pieces: list[Piece], mats: Materials) -> bytes:
    bin_parts: list[bytes] = []
    views: list[dict] = []
    accessors: list[dict] = []
    meshes: list[dict] = []
    nodes: list[dict] = []
    offset = 0

    def add_view(data: bytes, target: int) -> int:
        nonlocal offset
        padded = _pad(data)
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data), "target": target})
        bin_parts.append(padded)
        offset += len(padded)
        return len(views) - 1

    for p in pieces:
        prims = []
        for mat, xyz, tri in p.prims:
            used, inv = np.unique(tri.ravel(), return_inverse=True)
            pos = np.ascontiguousarray(xyz[used], dtype="<f4")
            idx = np.ascontiguousarray(inv.reshape(-1), dtype="<u4")
            accessors.append({"bufferView": add_view(pos.tobytes(), 34962), "componentType": 5126, "count": len(pos),
                              "type": "VEC3", "min": pos.min(axis=0).tolist(), "max": pos.max(axis=0).tolist()})
            a_pos = len(accessors) - 1
            accessors.append({"bufferView": add_view(idx.tobytes(), 34963), "componentType": 5125, "count": len(idx),
                              "type": "SCALAR"})
            prims.append({"attributes": {"POSITION": a_pos}, "indices": len(accessors) - 1, "material": mat, "mode": 4})
        meshes.append({"name": p.name, "primitives": prims})
        nodes.append({"name": p.name, "mesh": len(meshes) - 1, "extras": p.extras})

    gltf = {"asset": {"version": "2.0", "generator": "revit-demo viewer_export"}, "scene": 0,
            "scenes": [{"nodes": list(range(len(nodes)))}], "nodes": nodes, "meshes": meshes,
            "materials": mats.items, "accessors": accessors, "bufferViews": views,
            "buffers": [{"byteLength": offset}]}
    js = _pad(json.dumps(gltf, separators=(",", ":"), allow_nan=False).encode("utf-8"), b" ")
    binary = b"".join(bin_parts)
    total = 12 + 8 + len(js) + 8 + len(binary)
    return (struct.pack("<III", 0x46546C67, 2, total) + struct.pack("<II", len(js), 0x4E4F534A) + js
            + struct.pack("<II", len(binary), 0x004E4942) + binary)


def export_viewer(ifc_path: str | Path, out_dir: Path, scene: dict[str, Any], viewer_src: Path) -> dict[str, Any]:
    """Writes out_dir/{index.html, vendor/, model.glb, scene.json}: a folder any static web server can show."""
    import shutil
    out_dir.mkdir(parents=True, exist_ok=True)
    pieces, mats, info = collect(ifc_path)
    glb = build_glb(pieces, mats)
    (out_dir / "model.glb").write_bytes(glb)
    scene = {**scene, "ifc": {"file": Path(ifc_path).name, "schema": info["schema"], "counts": info["counts"]},
             "storeys": [{"name": n, "elevation": e} for n, e in info["storeys"]]}
    (out_dir / "scene.json").write_text(json.dumps(scene, ensure_ascii=False), encoding="utf-8")
    shutil.copy2(viewer_src / "index.html", out_dir / "index.html")
    dst = out_dir / "vendor"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(viewer_src / "vendor", dst)
    return {"dir": str(out_dir), "glb_bytes": len(glb), "elements": len(pieces), "counts": info["counts"],
            "triangles": int(sum(len(t) for p in pieces for _, _, t in p.prims))}
