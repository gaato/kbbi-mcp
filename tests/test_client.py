import json
from pathlib import Path

import pytest
from conftest import _as_mapping

import kbbi_mcp
import kbbi_mcp.server as server


@pytest.mark.anyio
async def test_create_client_can_call_tool(serve_fixture):
    serve_fixture("makan")

    async with kbbi_mcp.create_client() as client:
        # The SDK client validates structured content against the tool's outputSchema.
        result = await client.call_tool("kbbi_lookup", {"query": "makan"})

    payload = _as_mapping(result.structured_content)
    assert payload["found"] is True
    assert payload["query"] == "makan"
    assert payload["url"] == "https://kbbi.kemendikdasmen.go.id/entri/makan"
    assert [e["homograph"] for e in payload["entries"]] == [1, 2]
    assert payload["entries"][0]["senses"][10]["examples"][0]["meaning"] == (
        "tidak memperoleh angin"
    )


@pytest.mark.anyio
async def test_create_client_exposes_kbbi_resource_template(monkeypatch):
    async with kbbi_mcp.create_client() as client:
        templates = (await client.list_resource_templates()).resource_templates

    uri_templates = {t.uri_template for t in templates}
    assert "kbbi://{query}" in uri_templates


@pytest.mark.anyio
async def test_create_client_can_read_kbbi_resource(serve_fixture):
    serve_fixture("mempunyai")

    async with kbbi_mcp.create_client() as client:
        contents = (await client.read_resource("kbbi://mempunyai")).contents

    assert contents, "resource must return at least one content item"
    text = getattr(contents[0], "text", None)
    assert isinstance(text, str)

    payload = json.loads(text)
    assert payload["query"] == "mempunyai"
    assert payload["entries"][0]["root_words"] == ["punya"]


@pytest.mark.anyio
async def test_tool_metadata_follows_mcp_best_practices():
    async with kbbi_mcp.create_client() as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}

    tool = tools["kbbi_lookup"]
    assert tool.title == "KBBI Lookup"
    assert tool.icons
    assert tool.annotations is not None
    assert tool.annotations.read_only_hint is True
    assert tool.annotations.destructive_hint is False
    assert tool.annotations.idempotent_hint is True
    assert tool.annotations.open_world_hint is True


@pytest.mark.anyio
async def test_resource_template_is_json():
    async with kbbi_mcp.create_client() as client:
        templates = {
            t.uri_template: t for t in (await client.list_resource_templates()).resource_templates
        }

    template = templates["kbbi://{query}"]
    assert template.mime_type == "application/json"
    assert template.title == "KBBI Entry"


@pytest.mark.anyio
async def test_tool_errors_are_reported_as_tool_errors(monkeypatch):
    def boom(url: str, timeout_seconds: float) -> str:
        raise RuntimeError("network down")

    monkeypatch.setattr(server, "_fetch_html", boom)

    async with kbbi_mcp.create_client() as client:
        result = await client.call_tool("kbbi_lookup", {"query": "apel"})
        empty = await client.call_tool("kbbi_lookup", {"query": "  "})

    assert result.is_error
    assert "RuntimeError: network down" in result.content[0].text
    assert empty.is_error
    assert "must not be empty" in empty.content[0].text


@pytest.mark.anyio
async def test_readme_lists_tools_parameters_and_resources():
    readme = (Path(__file__).parent.parent / "README.rst").read_text()

    async with kbbi_mcp.create_client() as client:
        tools = (await client.list_tools()).tools
        templates = (await client.list_resource_templates()).resource_templates

    for tool in tools:
        assert f"``{tool.name}``" in readme
        schema = tool.input_schema
        for name in schema["properties"]:
            kind = "required" if name in schema.get("required", []) else "optional"
            assert f"``{name}`` ({schema['properties'][name]['type']}, {kind})" in readme
    for template in templates:
        assert f"``{template.uri_template}``" in readme
