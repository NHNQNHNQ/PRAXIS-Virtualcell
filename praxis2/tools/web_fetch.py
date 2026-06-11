"""WebFetchTool:模型可调用的"白名单域 fetch"工具(v0.16.0-beta P0 4/5)。

回归:此前模型想"查 doi / 看 uniprot entry / 取 arxiv abstract"只能纯文字
描述"我去查一下"。本工具补"GET 白名单域"这一缝。

设计(v0.16.0-beta 第一版):
- 白名单域(科研常用 ~12 个,可经 __init__ extra_allowed_hosts 扩展)
- 仅 HTTPS(防 MITM);仅 GET(无 POST / cookies / 自定义 header)
- 体积上限 max_bytes 默认 1MB,流式读 + 计数双保险
- 10s timeout(failed → ok=False 不抛)
- HTTP 4xx/5xx → ok=False 含 status(不抛 raise_for_status)
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from praxis2.tools.base import Tool, ToolResult

# 白名单域(suffix 匹配:host == domain 或 host.endswith("." + domain))
_DEFAULT_ALLOWED_HOSTS: set[str] = {
    # 文献 / DOI
    "doi.org",
    "dx.doi.org",
    "arxiv.org",
    "www.biorxiv.org",
    # NCBI 系列(pubmed/pmc/protein/nucleotide)
    "pubmed.ncbi.nlm.nih.gov",
    "www.ncbi.nlm.nih.gov",
    "pubchem.ncbi.nlm.nih.gov",
    # 蛋白 / 结构 / 序列
    "www.uniprot.org",
    "rest.uniprot.org",
    "www.rcsb.org",
    "files.rcsb.org",
    "www.ebi.ac.uk",
    # 通用百科 / 出版社
    "en.wikipedia.org",
    "zh.wikipedia.org",
    "www.nature.com",
    "www.science.org",
    "www.cell.com",
}

_DEFAULT_MAX_BYTES = 1_000_000  # 1 MB
_DEFAULT_TIMEOUT_S = 10.0


def _host_allowed(host: str, allowed: set[str]) -> bool:
    """suffix 匹配:host == d 或 host.endswith('.' + d)。"""
    h = (host or "").lower()
    for d in allowed:
        if h == d or h.endswith("." + d):
            return True
    return False


class WebFetchTool(Tool):
    """GET 白名单域 URL,返 status + 截断后的 text。"""

    name = "WebFetch"
    description = (
        "GET 白名单科研域(doi.org / arxiv / pubmed / uniprot / rcsb / wikipedia "
        "/ nature.com / cell.com / science.org 等)的 URL,返 status + text。"
        "仅 HTTPS,无 POST / cookies,max_bytes 默认 1MB(超出截断 + 标记)。"
        "4xx/5xx → ok=False 含 status,不抛。"
    )
    rmcp_op = None  # 读外部类工具不受相位门

    def __init__(
        self,
        *,
        extra_allowed_hosts: list[str] | None = None,
        timeout_s: float = _DEFAULT_TIMEOUT_S,
        max_bytes_default: int = _DEFAULT_MAX_BYTES,
    ) -> None:
        self._allowed = set(_DEFAULT_ALLOWED_HOSTS)
        if extra_allowed_hosts:
            self._allowed.update(h.lower() for h in extra_allowed_hosts)
        self._timeout_s = timeout_s
        self._max_bytes_default = max_bytes_default

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": (
                        "完整 HTTPS URL,host 必须在白名单(doi.org/arxiv.org/"
                        "pubmed.ncbi.nlm.nih.gov/www.uniprot.org/www.rcsb.org/"
                        "en.wikipedia.org/www.nature.com 等)"
                    ),
                },
                "max_bytes": {
                    "type": "integer",
                    "description": (
                        "响应体上限字节(默认 1_000_000=1MB,超出截断+truncated=True)"
                    ),
                    "default": _DEFAULT_MAX_BYTES,
                },
            },
            "required": ["url"],
        }

    async def run(self, payload: dict[str, Any]) -> ToolResult:
        url = (payload.get("url") or "").strip()
        max_bytes = int(payload.get("max_bytes") or self._max_bytes_default)
        max_bytes = max(1024, min(max_bytes, 10_000_000))  # 1KB..10MB cap

        if not url:
            return ToolResult(ok=False, error="缺 url(必填)")

        try:
            parsed = urlparse(url)
        except ValueError as e:
            return ToolResult(ok=False, error=f"URL 解析失败:{e}")

        if not parsed.scheme or not parsed.netloc:
            return ToolResult(ok=False, error=f"无效 URL {url!r}(缺 scheme / host)")

        if parsed.scheme.lower() != "https":
            return ToolResult(
                ok=False,
                error=(
                    f"仅允许 https:// scheme(收到 {parsed.scheme!r}, 防 MITM)。"
                    "无 https 镜像时请直接给用户提示。"
                ),
            )

        host = parsed.hostname or ""
        if not _host_allowed(host, self._allowed):
            return ToolResult(
                ok=False,
                error=(
                    f"非白名单域 {host!r}(not allowed)。"
                    f"白名单(suffix 匹配):{sorted(self._allowed)}"
                ),
                recovery_hint=(
                    "改用白名单内域名 / 同等内容的 DOI/PubMed/arxiv 镜像。"
                ),
            )

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_s, follow_redirects=False,
            ) as client:
                resp = await client.get(url)
        except httpx.TimeoutException as e:
            return ToolResult(
                ok=False,
                error=f"请求超时(>{self._timeout_s}s):{e}",
                recovery_hint="该域响应慢,可改用其他白名单镜像或重试。",
            )
        except httpx.HTTPError as e:
            return ToolResult(
                ok=False,
                error=f"HTTP 错误:{type(e).__name__}: {e}",
            )

        if resp.status_code >= 400:
            return ToolResult(
                ok=False,
                error=(
                    f"HTTP {resp.status_code} from {host!r}"
                    f"(content_length={resp.headers.get('content-length','?')})"
                ),
                value={
                    "url": url,
                    "status": resp.status_code,
                    "host": host,
                },
            )

        raw = resp.content
        size_bytes = len(raw)
        truncated = size_bytes > max_bytes
        if truncated:
            raw = raw[:max_bytes]

        # text decode(content-type 不可靠,统一 utf-8 with replace)
        text = raw.decode("utf-8", errors="replace")
        if truncated:
            text = text + f"\n…[截断:原 {size_bytes} bytes 超 max_bytes={max_bytes}]"

        return ToolResult(
            ok=True,
            value={
                "url": url,
                "host": host,
                "status": resp.status_code,
                "content_type": resp.headers.get("content-type", ""),
                "size_bytes": size_bytes,
                "truncated": truncated,
                "text": text,
            },
        )
