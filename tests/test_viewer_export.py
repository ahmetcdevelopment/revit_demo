"""IFC -> GLB for the browser viewer: valid glTF, no NaN, one node per product, vendored three.js complete."""

import json
import re
import struct
from pathlib import Path

import numpy as np
import pytest

from brain.backends.ifc import IfcBackend
from brain.viewer_export import Materials, Piece, build_glb, export_viewer
from tests.test_planner import parcel, spec, zoning  # noqa: F401

VIEWER = Path(__file__).resolve().parents[1] / "src" / "viewer"


def parse_glb(data: bytes):
    magic, version, length = struct.unpack("<III", data[:12])
    assert magic == 0x46546C67 and version == 2 and length == len(data)
    jlen, jtype = struct.unpack("<II", data[12:20])
    assert jtype == 0x4E4F534A
    gltf = json.loads(data[20:20 + jlen].decode("utf-8"))
    blen, btype = struct.unpack("<II", data[20 + jlen:28 + jlen])
    assert btype == 0x004E4942 and 28 + jlen + blen == len(data)
    return gltf, data[28 + jlen:]


def one_triangle_piece(m: Materials, alpha: float = 1.0) -> Piece:
    xyz = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [9, 9, 9]], dtype=np.float32)
    tri = np.array([[0, 1, 2]], dtype=np.uint32)
    p = Piece(name="W", extras={"ifc": "IfcWall", "storey": "L0"})
    p.prims.append((m.get((0.5, 0.5, 0.5), alpha), xyz, tri))
    return p


def test_glb_container_and_accessors_are_consistent():
    m = Materials()
    gltf, binary = parse_glb(build_glb([one_triangle_piece(m), one_triangle_piece(m, 0.4)], m))
    assert len(gltf["nodes"]) == 2 and gltf["nodes"][0]["extras"]["ifc"] == "IfcWall"
    pos = next(a for a in gltf["accessors"] if a["type"] == "VEC3")
    assert pos["count"] == 3                      # only the vertices the triangle uses (the stray one is dropped)
    for v in gltf["bufferViews"]:
        assert v["byteOffset"] % 4 == 0 and v["byteOffset"] + v["byteLength"] <= len(binary)
    assert {mt["alphaMode"] for mt in gltf["materials"]} == {"OPAQUE", "BLEND"}


def test_nan_never_reaches_the_file():
    m = Materials()
    m.get((0.5, 0.5, 0.5), float("nan"))
    with pytest.raises(ValueError):
        build_glb([one_triangle_piece(m)], m)     # allow_nan=False: it must fail loudly, not write NaN


def test_yup_conversion_in_a_real_ifc(spec, tmp_path):
    ifc = tmp_path / "m.ifc"
    IfcBackend().write(spec, ifc)
    out = tmp_path / "viewer"
    info = export_viewer(ifc, out, {"title": "t"}, VIEWER)
    gltf, _ = parse_glb((out / "model.glb").read_bytes())
    assert info["elements"] == len(gltf["nodes"]) > 300 and info["triangles"] > 1000
    assert "NaN" not in (out / "scene.json").read_text(encoding="utf-8")
    walls = [n for n in gltf["nodes"] if n["extras"]["ifc"] == "IfcWall"]
    assert len(walls) == len(spec.walls)
    top = max(a["max"][1] for a in gltf["accessors"] if a["type"] == "VEC3")        # Y is up
    assert 8.0 < top < 10.5                                                          # a 9 m building (roof level 9.0)
    storeys = json.loads((out / "scene.json").read_text(encoding="utf-8"))["storeys"]
    assert [round(s["elevation"], 2) for s in storeys] == [0.0, 3.0, 6.0, 9.0]


def test_viewer_folder_is_self_contained(spec, tmp_path):
    ifc = tmp_path / "m.ifc"
    IfcBackend().write(spec, ifc)
    out = tmp_path / "viewer"
    export_viewer(ifc, out, {"title": "t"}, VIEWER)
    html = (out / "index.html").read_text(encoding="utf-8")
    imports = json.loads(re.search(r'<script type="importmap">(.*?)</script>', html, re.S).group(1))["imports"]
    assert imports["three"].startswith("./vendor/") and imports["three/addons/"].startswith("./vendor/")
    assert (out / "vendor/three/three.module.js").exists()
    for rel in ("controls/OrbitControls.js", "loaders/GLTFLoader.js", "utils/BufferGeometryUtils.js"):
        assert (out / "vendor/three/addons" / rel).exists()
    assert not re.search(r"https?://(?!127\.0\.0\.1)", html.replace("http://www.w3.org", "")), "viewer must work offline"
    assert (VIEWER / "vendor/three/LICENSE").read_text(encoding="utf-8").startswith("The MIT License")
