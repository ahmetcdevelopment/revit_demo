"""The server must start with the exact command in .mcp.json (what Claude runs), not just when imported by tests.

A broken launch command once shipped because every other check imported `brain` with src/ already on the path;
Claude then saw CONNECTION_CLOSED. This test starts the real process the way a client does.
"""

import json
import os
import tempfile
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parents[1]


def launch() -> StdioServerParameters:
    cfg = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["revit-demo"]
    args = [str(ROOT) if a == "." else a for a in cfg["args"]]
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return StdioServerParameters(command=cfg["command"], args=args, env=env, cwd=tempfile.gettempdir())


def test_the_configured_command_starts_a_working_server():
    async def go():
        async with stdio_client(launch()) as streams, ClientSession(*streams) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            r = await session.call_tool("load_parcel", {"name": "karatay-buyuksinan-1495-26"})
            return names, r.structured_content
    names, loaded = anyio.run(go)
    assert {"load_parcel", "plan_building", "build_in_revit", "verify_model", "generate_report"} <= names
    assert loaded["ok"] and loaded["parcel"]["parcel_id"] == "karatay-buyuksinan-1495-26"
