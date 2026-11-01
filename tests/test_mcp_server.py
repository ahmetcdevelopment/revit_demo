"""The MCP surface: tool list, argument schemas, and a call through the protocol layer."""

import anyio
import pytest

from brain.mcp_server import create_server
from brain.service import Session
from tests.fake_revit import FakeRevit

EXPECTED = {"list_inputs", "load_parcel", "check_zoning", "plan_building", "validate_spec", "build_in_revit",
            "verify_model", "export_views", "export_ifc", "export_viewer", "generate_report", "get_status"}


@pytest.fixture
def server(tmp_path):
    return create_server(Session(out_dir=tmp_path, backend=FakeRevit(online=False)))


def run(coro_fn):
    return anyio.run(coro_fn)


def test_tools_are_listed_with_descriptions(server):
    async def go():
        return await server.list_tools()
    tools = run(go)
    assert {t.name for t in tools} == EXPECTED
    assert all(t.description and len(t.description) > 30 for t in tools)


def test_argument_schemas_have_defaults_a_model_can_rely_on(server):
    async def go():
        return {t.name: t.input_schema for t in await server.list_tools()}
    schemas = run(go)
    assert schemas["load_parcel"]["required"] == ["name"]
    build = schemas["build_in_revit"]["properties"]
    assert build["dry_run"]["default"] is True and build["new_project"]["default"] is False
    assert schemas["plan_building"]["properties"]["floors"]["default"] == 3


def test_call_through_the_protocol_layer(server):
    async def go():
        a = await server.call_tool("load_parcel", {"name": "karatay-buyuksinan-1495-26"})
        b = await server.call_tool("plan_building", {})
        c = await server.call_tool("build_in_revit", {"dry_run": True})
        return a, b, c
    a, b, c = run(go)
    assert a.structured_content["ok"] and b.structured_content["spec_id"]
    assert c.structured_content["mode"] == "offline_dry_run"


def test_bad_arguments_are_rejected_by_the_schema(server):
    async def go():
        return await server.call_tool("plan_building", {"floors": "three"})
    with pytest.raises(Exception):
        run(go)
