"""RevitBackend protocol tests against an in-process fake bridge (no Revit needed)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from brain.backends.revit import BridgeUnavailable, RevitBackend, RevitBridgeError
from brain.compiler import compile_spec
from tests.test_planner import parcel, spec, zoning  # noqa: F401

TOKEN = "secret-token"


class FakeBridge(BaseHTTPRequestHandler):
    log: list = []

    def log_message(self, *a):  # silence
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.headers.get("X-Bridge-Token") != TOKEN:
            return self._send(401, {"id": body["id"], "ok": False,
                                    "error": {"code": "unauthorized", "message": "bad token"}})
        FakeBridge.log.append(body)
        m, p = body["method"], body["params"]
        if m == "ping":
            res = {"pong": True, "ops": ["create_level"]}
        elif m == "apply_ops":
            if any(o["op"] != "create_level" for o in p["ops"]):
                bad = next(o for o in p["ops"] if o["op"] != "create_level")
                return self._send(200, {"id": body["id"], "ok": False,
                                        "error": {"code": "unsupported_op", "message": "nope",
                                                  "op_id": bad["op_id"]}})
            res = {"created": len(p["ops"]), "dry_run": p["dry_run"]}
        elif m == "export_views":
            res = {"dir": p["dir"], "files": []}
        else:
            return self._send(200, {"id": body["id"], "ok": False,
                                    "error": {"code": "unknown_method", "message": m}})
        self._send(200, {"id": body["id"], "ok": True, "result": res})

    def _send(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def bridge(tmp_path):
    FakeBridge.log = []
    server = HTTPServer(("127.0.0.1", 0), FakeBridge)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    ep = tmp_path / "endpoint.json"
    ep.write_text(json.dumps({"port": server.server_port, "token": TOKEN}))
    yield RevitBackend(ep, timeout=5)
    server.shutdown()


def test_ping(bridge):
    assert bridge.ping()["pong"] is True
    assert FakeBridge.log[0]["method"] == "ping" and FakeBridge.log[0]["id"]


def test_apply_ops_sends_snake_case_ops(bridge, spec):
    levels = [o for o in compile_spec(spec) if o.op == "create_level"]
    res = bridge.apply_ops(levels, spec.spec_id, dry_run=True)
    assert res == {"created": 4, "dry_run": True}
    sent = FakeBridge.log[-1]["params"]
    assert sent["spec_id"] == spec.spec_id
    assert set(sent["ops"][0]) == {"op_id", "op", "spec_ref", "depends_on", "args"}
    assert sent["ops"][0]["args"]["elevation"] == 0.0


def test_error_payload_becomes_exception_with_op_id(bridge, spec):
    walls = [o for o in compile_spec(spec) if o.op == "create_wall"][:1]
    with pytest.raises(RevitBridgeError) as e:
        bridge.apply_ops(walls, spec.spec_id)
    assert e.value.code == "unsupported_op" and e.value.op_id == walls[0].op_id


def test_apply_supported_sends_only_ops_the_addin_implements(bridge, spec):
    ops = compile_spec(spec)
    res, skipped = bridge.apply_supported(ops, spec.spec_id, prune=True)
    sent = FakeBridge.log[-1]["params"]
    assert {o["op"] for o in sent["ops"]} == {"create_level"} and res["created"] == 4
    assert sent["prune"] is True
    assert "create_wall" in skipped and "create_level" not in skipped


def test_export_views_sends_absolute_directory(bridge, tmp_path):
    out = bridge.export_views(tmp_path / "views")
    assert out["dir"] == str((tmp_path / "views").resolve())


def test_bad_token_rejected(bridge, tmp_path):
    ep = json.loads(bridge.endpoint_file.read_text())
    ep["token"] = "wrong"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(ep))
    with pytest.raises(RevitBridgeError) as e:
        RevitBackend(bad, timeout=5).ping()
    assert e.value.code == "unauthorized"


def test_unknown_method(bridge):
    with pytest.raises(RevitBridgeError) as e:
        bridge.call("explode")
    assert e.value.code == "unknown_method"


def test_missing_endpoint_means_revit_not_running(tmp_path):
    with pytest.raises(BridgeUnavailable):
        RevitBackend(tmp_path / "none.json").ping()


def test_stale_endpoint_means_revit_not_running(tmp_path):
    ep = tmp_path / "stale.json"
    ep.write_text(json.dumps({"port": 1, "token": "x"}))
    with pytest.raises(BridgeUnavailable):
        RevitBackend(ep, timeout=2).ping()
