"""Talks to the MCP server over real stdio, exactly as Claude launches it, and runs the whole flow.

usage: uv run python tools/mcp_smoke.py [--build] [--fresh]
It starts the server with the SAME command as .mcp.json (no PYTHONPATH, from a different working directory), so a
broken launch command shows up here and not first inside Claude. Without --build it stops after the dry run
(works without Revit); with --build it also builds the model in the open Revit project and calls verify_model.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parents[1]


def launch_params() -> StdioServerParameters:
    """The launch command from .mcp.json, with `.` resolved against the repo like Claude Code does."""
    cfg = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["revit-demo"]
    args = [str(ROOT) if a == "." else a for a in cfg["args"]]
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return StdioServerParameters(command=cfg["command"], args=args, env=env, cwd=tempfile.gettempdir())


def short(result) -> dict:
    data = result.structured_content or json.loads(result.content[0].text)
    return {k: v for k, v in data.items() if k not in ("report", "validation", "parcel", "known_gaps", "rows")}


async def main(build: bool) -> int:
    async with stdio_client(launch_params()) as streams, ClientSession(*streams) as session:
        await session.initialize()
        tools = await session.list_tools()
        print("tools:", ", ".join(t.name for t in tools.tools))
        steps = [("get_status", {}), ("list_inputs", {}),
                 ("load_parcel", {"name": "karatay-buyuksinan-1495-26"}), ("check_zoning", {}),
                 ("plan_building", {}), ("build_in_revit", {"dry_run": True})]
        if build:
            steps += [("build_in_revit", {"dry_run": False, "new_project": "--fresh" in sys.argv}), ("verify_model", {})]
        ok = True
        for name, args in steps:
            r = await session.call_tool(name, args)
            data = short(r)
            ok &= bool(data.get("ok", True))
            print(f"[{name}]", json.dumps(data, ensure_ascii=False)[:420])
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(anyio.run(main, "--build" in sys.argv))
