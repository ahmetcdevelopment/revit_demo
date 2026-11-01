"""RevitBackend: JSON-RPC client for the RevitBridge add-in (loopback HTTP + token).

The add-in writes %LOCALAPPDATA%\\RevitBridge\\endpoint.json ({port, token, pid, ...}) when Revit
starts; this client reads it. Override with the REVIT_BRIDGE_ENDPOINT environment variable.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from ..schemas import Op


class BridgeUnavailable(RuntimeError):
    """Revit is not running, the add-in is not loaded, or the endpoint is stale."""


class RevitBridgeError(RuntimeError):
    def __init__(self, code: str, message: str, op_id: str | None = None):
        super().__init__(f"{code}: {message}" + (f" (op {op_id})" if op_id else ""))
        self.code, self.message, self.op_id = code, message, op_id


def default_endpoint_path() -> Path:
    env = os.environ.get("REVIT_BRIDGE_ENDPOINT")
    if env:
        return Path(env)
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "RevitBridge" / "endpoint.json"


class RevitBackend:
    def __init__(self, endpoint_file: str | Path | None = None, timeout: float = 620.0):
        self.endpoint_file = Path(endpoint_file) if endpoint_file else default_endpoint_path()
        self.timeout = timeout

    # ------------------------------------------------------------------ transport
    def _endpoint(self) -> dict[str, Any]:
        try:
            return json.loads(self.endpoint_file.read_text(encoding="utf-8"))
        except FileNotFoundError as e:
            raise BridgeUnavailable(
                f"{self.endpoint_file} not found: start Revit with the RevitBridge add-in loaded") from e

    def call(self, method: str, **params: Any) -> Any:
        ep = self._endpoint()
        body = json.dumps({"id": uuid.uuid4().hex, "method": method, "params": params},
                          ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{ep['port']}/rpc/", data=body, method="POST",
            headers={"Content-Type": "application/json", "X-Bridge-Token": ep["token"]})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read().decode("utf-8"))
            except Exception:  # noqa: BLE001
                raise RevitBridgeError("http_" + str(e.code), e.reason) from e
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            raise BridgeUnavailable(f"cannot reach Revit bridge on port {ep.get('port')}: {e}") from e
        if not payload.get("ok"):
            err = payload.get("error") or {}
            raise RevitBridgeError(err.get("code", "error"), err.get("message", ""), err.get("op_id"))
        return payload.get("result")

    # ------------------------------------------------------------------ API
    def ping(self) -> dict[str, Any]:
        return self.call("ping")

    def status(self) -> dict[str, Any]:
        return self.call("status")

    def new_project(self, path: str | Path, template: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"path": str(path)}
        if template:
            params["template"] = template
        return self.call("new_project", **params)

    def apply_ops(self, ops: list[Op], spec_id: str, dry_run: bool = False,
                  prune: bool = False) -> dict[str, Any]:
        return self.call("apply_ops", ops=[o.model_dump(mode="json") for o in ops],
                         spec_id=spec_id, dry_run=dry_run, prune=prune)

    def supported_ops(self) -> set[str]:
        return set(self.ping()["ops"])

    def apply_supported(self, ops: list[Op], spec_id: str, **kw: Any) -> tuple[dict[str, Any], list[str]]:
        """Apply only the ops the add-in implements; returns (result, skipped op names)."""
        ok = self.supported_ops()
        skipped = sorted({o.op for o in ops if o.op not in ok})
        return self.apply_ops([o for o in ops if o.op in ok], spec_id, **kw), skipped

    def read_back(self) -> dict[str, Any]:
        return self.call("read_back")

    def export_views(self, directory: str | Path, pixels: int = 1800) -> dict[str, Any]:
        """Export the 3D view and every floor plan as PNG into `directory` (absolute path)."""
        return self.call("export_views", dir=str(Path(directory).resolve()), pixels=pixels)

    def show_3d(self) -> dict[str, Any]:
        """Bring the 3D view to the front in Revit."""
        return self.call("show_3d")

    def export_ifc(self, directory: str | Path, name: str = "revit.ifc", **project: str) -> dict[str, Any]:
        """Revit's own IFC4 export into `directory`; project_name / building_name / address fill IfcProject etc."""
        return self.call("export_ifc", dir=str(Path(directory).resolve()), name=name, **project)

    def inspect(self) -> dict[str, Any]:
        """Types and families available in the open document."""
        return self.call("inspect")
