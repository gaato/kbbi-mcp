import json

import pytest
from conftest import _as_mapping

import kbbi_mcp
import kbbi_mcp.server as server


@pytest.mark.anyio
async def test_create_client_can_call_tool(monkeypatch):
    def fake_lookup_serialized(query: str):
        assert query == "apel"
        return {
            "source_url": "https://kbbi.kemendikdasmen.go.id/entri/apel",
            "entries": [
                {
                    "headword": "apel",
                    "sense_number": "",
                    "root_words": [],
                    "pronunciation": "",
                    "nonstandard_forms": [],
                    "variants": [],
                    "definitions": [
                        {
                            "word_classes": [],
                            "glosses": ["buah"],
                            "note": "",
                            "examples": [],
                        }
                    ],
                }
            ],
        }

    monkeypatch.setattr(server, "_lookup_serialized", fake_lookup_serialized)

    async with kbbi_mcp.create_client() as client:
        result = await client.call_tool("kbbi_lookup", {"query": "apel"})

    payload = _as_mapping(result.data)
    assert payload["found"] is True
    assert payload["query"] == "apel"
    assert payload["url"] == "https://kbbi.kemendikdasmen.go.id/entri/apel"
    assert len(payload["entries"]) == 1


@pytest.mark.anyio
async def test_create_client_exposes_kbbi_resource_template(monkeypatch):
    async with kbbi_mcp.create_client() as client:
        templates = await client.list_resource_templates()

    uri_templates = {t.uri_template for t in templates}
    assert "kbbi://{query}" in uri_templates


@pytest.mark.anyio
async def test_create_client_can_read_kbbi_resource(monkeypatch):
    def fake_lookup_serialized(query: str):
        assert query == "apel"
        return {
            "source_url": "https://kbbi.kemendikdasmen.go.id/entri/apel",
            "entries": [],
            "suggestions": ["apel-apel"],
        }

    monkeypatch.setattr(server, "_lookup_serialized", fake_lookup_serialized)

    async with kbbi_mcp.create_client() as client:
        contents = await client.read_resource("kbbi://apel")

    assert contents, "resource must return at least one content item"
    text = getattr(contents[0], "text", None)
    assert isinstance(text, str)

    payload = json.loads(text)
    assert payload["query"] == "apel"
    assert payload["suggestions"] == ["apel-apel"]


@pytest.mark.anyio
async def test_tool_metadata_follows_mcp_best_practices():
    async with kbbi_mcp.create_client() as client:
        tools = {t.name: t for t in await client.list_tools()}

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
        templates = {t.uri_template: t for t in await client.list_resource_templates()}

    template = templates["kbbi://{query}"]
    assert template.mime_type == "application/json"
    assert template.title == "KBBI Entry"


@pytest.mark.anyio
async def test_tool_errors_are_reported_as_tool_errors(monkeypatch):
    def boom(_: str):
        raise RuntimeError("network down")

    monkeypatch.setattr(server, "_lookup_serialized", boom)

    async with kbbi_mcp.create_client() as client:
        result = await client.call_tool("kbbi_lookup", {"query": "apel"}, raise_on_error=False)
        empty = await client.call_tool("kbbi_lookup", {"query": "  "}, raise_on_error=False)

    assert result.is_error
    assert "RuntimeError: network down" in result.content[0].text
    assert empty.is_error
    assert "must not be empty" in empty.content[0].text
