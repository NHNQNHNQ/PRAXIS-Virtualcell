from __future__ import annotations

import asyncio

import httpx
import respx

from praxis2.agents.loader import resolve_agent
from praxis2.server.chat_registry import build_chat_registry
from praxis2.tools.web_fetch import WebFetchTool


def test_web_fetch_registered_in_chat_registry():
    sel = resolve_agent("virtualcell", user_query="hi")
    reg = build_chat_registry(selection=sel)
    assert "WebFetch" in [t["name"] for t in reg.anthropic_tools()]


@respx.mock
def test_web_fetch_doi_org_success():

    respx.get("https://doi.org/10.1016/j.cell.2015.01.035").mock(
        return_value=httpx.Response(
            200,
            text="<html><body>Stiffler 2015 paper landing page</body></html>",
            headers={"content-type": "text/html; charset=utf-8"},
        )
    )
    t = WebFetchTool()
    r = asyncio.run(t.run({"url": "https://doi.org/10.1016/j.cell.2015.01.035"}))
    assert r.ok
    v = r.value
    assert v["status"] == 200
    assert "Stiffler 2015" in v["text"]
    assert v["truncated"] is False


def test_web_fetch_non_whitelist_rejected():

    t = WebFetchTool()
    r = asyncio.run(t.run({"url": "https://evil.example.com/secret"}))
    assert not r.ok
    assert (
        "allowlisted" in (r.error or "")
        or "whitelist" in (r.error or "").lower()
        or "not allowed" in (r.error or "").lower()
    )  # noqa: E501


def test_web_fetch_http_scheme_rejected():

    t = WebFetchTool()
    r = asyncio.run(t.run({"url": "http://doi.org/10.0/abc"}))
    assert not r.ok
    assert "https" in (r.error or "").lower() or "scheme" in (r.error or "").lower()


def test_web_fetch_invalid_url_rejected():
    t = WebFetchTool()
    r = asyncio.run(t.run({"url": "not a url"}))
    assert not r.ok


@respx.mock
def test_web_fetch_size_cap_truncates():

    big = "X" * 200_000
    respx.get("https://en.wikipedia.org/wiki/Enzyme").mock(
        return_value=httpx.Response(
            200,
            text=big,
            headers={"content-type": "text/html"},
        )
    )
    t = WebFetchTool()
    r = asyncio.run(
        t.run(
            {
                "url": "https://en.wikipedia.org/wiki/Enzyme",
                "max_bytes": 10_000,
            }
        )
    )
    assert r.ok
    assert r.value["truncated"] is True
    assert len(r.value["text"]) <= 10_500


@respx.mock
def test_web_fetch_4xx_returns_error_but_not_raise():

    respx.get("https://arxiv.org/abs/9999.99999").mock(
        return_value=httpx.Response(404, text="Not Found"),
    )
    t = WebFetchTool()
    r = asyncio.run(t.run({"url": "https://arxiv.org/abs/9999.99999"}))
    assert not r.ok
    assert "404" in (r.error or "")


@respx.mock
def test_web_fetch_timeout_handled():

    respx.get("https://www.uniprot.org/uniprotkb/P62593").mock(
        side_effect=httpx.TimeoutException("simulated"),
    )
    t = WebFetchTool()
    r = asyncio.run(t.run({"url": "https://www.uniprot.org/uniprotkb/P62593"}))
    assert not r.ok
    assert "timed out" in (r.error or "") or "timeout" in (r.error or "").lower()


def test_web_fetch_input_schema_complete():
    t = WebFetchTool()
    s = t.input_schema()
    assert s["required"] == ["url"]
    assert "url" in s["properties"]
    assert "max_bytes" in s["properties"]


def test_web_fetch_rmcp_op_is_none():

    assert WebFetchTool().rmcp_op is None


def test_web_fetch_missing_url_returns_error():
    t = WebFetchTool()
    r = asyncio.run(t.run({}))
    assert not r.ok


@respx.mock
def test_web_fetch_custom_extra_allowed_hosts():

    respx.get("https://my-allowed.example.com/x").mock(
        return_value=httpx.Response(200, text="ok"),
    )
    t = WebFetchTool(extra_allowed_hosts=["my-allowed.example.com"])
    r = asyncio.run(t.run({"url": "https://my-allowed.example.com/x"}))
    assert r.ok
    assert r.value["text"] == "ok"
