"""Serves the browser viewer (out/viewer) on localhost and opens it. Build it first: MCP tool export_viewer, or
    uv run python tools/view.py --build      (plans the real parcel, exports the viewer from the best IFC available)
usage: uv run python tools/view.py [--build] [--port 8765] [--no-browser]
"""

from __future__ import annotations

import argparse
import functools
import http.server
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    out = ROOT / "out" / "viewer"
    if a.build or not (out / "model.glb").exists():
        from brain.service import Session
        s = Session()
        for step in (lambda: s.load_parcel("karatay-buyuksinan-1495-26"), s.check_zoning, s.plan_building, s.export_viewer):
            r = step()
            if not r["ok"]:
                print("failed:", r.get("error"), "|", r.get("hint"))
                return 1
        print(f"viewer built: {r['elements']} elements, {r['glb_bytes'] / 1e6:.1f} MB, {r['triangles']:,} triangles")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(out))
    handler.extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                              ".js": "text/javascript", ".glb": "model/gltf-binary", ".json": "application/json"}
    server = http.server.ThreadingHTTPServer(("127.0.0.1", a.port), handler)
    url = f"http://127.0.0.1:{a.port}/"
    print("serving", out, "at", url, "(Ctrl+C to stop)")
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
