"""WebFetchTool 单测(v0.16.0-beta P0 4/5)。

回归:此前模型在 chat 里想"查一下 doi:10.X/Y 是什么 / 看一下 uniprot P62593 entry"
只能纯文字描述"我去查一下" — 没有工具能真 fetch。本工具补"白名单域 fetch"
这一缝。

设计:
- 白名单域(科研常用):doi.org / arxiv.org / pubmed.ncbi.nlm.nih.gov /
  www.ncbi.nlm.nih.gov / uniprot.org / rcsb.org(PDB) / wikipedia.org /
  en.wikipedia.org / nature.com / science.org / cell.com / pubchem.ncbi.nlm.nih.gov
- 体积上限:1 MB(content_length 检查 + 流式 bytes 计数双保险)
- timeout:10s
- HTTP only(GET);无 POST,无 cookies,无 redirect-cross-domain
"""
from __future__ import annotations

import asyncio
from typing import Any

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
    """fetch doi.org URL(白名单)→ 返 status + text。"""
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
    """非白名单域 → 拒绝(不发请求)。"""
    t = WebFetchTool()
    r = asyncio.run(t.run({"url": "https://evil.example.com/secret"}))
    assert not r.ok
    assert "白名单" in (r.error or "") or "whitelist" in (r.error or "").lower() or "not allowed" in (r.error or "").lower()


def test_web_fetch_http_scheme_rejected():
    """http:// 拒(只允许 https://,防 MITM)。"""
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
    """响应 > max_bytes → 截断 + truncated=True。"""
    big = "X" * 200_000
    respx.get("https://en.wikipedia.org/wiki/Enzyme").mock(
        return_value=httpx.Response(
            200,
            text=big,
            headers={"content-type": "text/html"},
        )
    )
    t = WebFetchTool()
    r = asyncio.run(t.run({
        "url": "https://en.wikipedia.org/wiki/Enzyme",
        "max_bytes": 10_000,
    }))
    assert r.ok
    assert r.value["truncated"] is True
    assert len(r.value["text"]) <= 10_500  # 截断 + 标记


@respx.mock
def test_web_fetch_4xx_returns_error_but_not_raise():
    """HTTP 4xx → ok=False,但 error 含 status 信息(不抛异常)。"""
    respx.get("https://arxiv.org/abs/9999.99999").mock(
        return_value=httpx.Response(404, text="Not Found"),
    )
    t = WebFetchTool()
    r = asyncio.run(t.run({"url": "https://arxiv.org/abs/9999.99999"}))
    assert not r.ok
    assert "404" in (r.error or "")


@respx.mock
def test_web_fetch_timeout_handled():
    """请求超时 → ok=False,error 含 timeout。"""
    respx.get("https://www.uniprot.org/uniprotkb/P62593").mock(
        side_effect=httpx.TimeoutException("simulated"),
    )
    t = WebFetchTool()
    r = asyncio.run(t.run({"url": "https://www.uniprot.org/uniprotkb/P62593"}))
    assert not r.ok
    assert "超时" in (r.error or "") or "timeout" in (r.error or "").lower()


def test_web_fetch_input_schema_complete():
    t = WebFetchTool()
    s = t.input_schema()
    assert s["required"] == ["url"]
    assert "url" in s["properties"]
    assert "max_bytes" in s["properties"]


def test_web_fetch_rmcp_op_is_none():
    """fetch 类(读外部)不受相位门约束。"""
    assert WebFetchTool().rmcp_op is None


def test_web_fetch_missing_url_returns_error():
    t = WebFetchTool()
    r = asyncio.run(t.run({}))
    assert not r.ok


@respx.mock
def test_web_fetch_custom_extra_allowed_hosts():
    """构造时传 extra_allowed_hosts → 该域也放行(测试场景用)。"""
    respx.get("https://my-allowed.example.com/x").mock(
        return_value=httpx.Response(200, text="ok"),
    )
    t = WebFetchTool(extra_allowed_hosts=["my-allowed.example.com"])
    r = asyncio.run(t.run({"url": "https://my-allowed.example.com/x"}))
    assert r.ok
    assert r.value["text"] == "ok"
