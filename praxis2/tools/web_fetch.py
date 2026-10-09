from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from praxis2.tools.base import Tool, ToolResult

_DEFAULT_ALLOWED_HOSTS: set[str] = {
    "doi.org",
    "dx.doi.org",
    "arxiv.org",
    "www.biorxiv.org",
    "pubmed.ncbi.nlm.nih.gov",
    "www.ncbi.nlm.nih.gov",
    "pubchem.ncbi.nlm.nih.gov",
    "www.uniprot.org",
    "rest.uniprot.org",
    "www.rcsb.org",
    "files.rcsb.org",
    "www.ebi.ac.uk",
    "en.wikipedia.org",
    "zh.wikipedia.org",
    "www.nature.com",
    "www.science.org",
    "www.cell.com",
}

_DEFAULT_MAX_BYTES = 1_000_000  # 1 MB
_DEFAULT_TIMEOUT_S = 10.0


def _host_allowed(host: str, allowed: set[str]) -> bool:

    h = (host or "").lower()
    for d in allowed:
        if h == d or h.endswith("." + d):
            return True
    return False


class WebFetchTool(Tool):
    name = "WebFetch"
    description = (
        "Fetch an allowlisted scientific HTTPS URL. Retur"
        "n status and text without POST or cookies. The d"
        "efault limit is 1 MB with explicit truncation; H"
        "TTP errors return ok=False and their status."
    )
    rmcp_op = None

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
                    "description": ("Complete HTTPS URL on an allowlisted scientific domain"),
                },
                "max_bytes": {
                    "type": "integer",
                    "description": ("Maximum response bytes, default 1,000,000; larger responses set truncated=True"),
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
            return ToolResult(ok=False, error="Missing required url")

        try:
            parsed = urlparse(url)
        except ValueError as e:
            return ToolResult(ok=False, error=f"URL parsing failed:{e}")

        if not parsed.scheme or not parsed.netloc:
            return ToolResult(ok=False, error=f"Invalid URL {url!r}(scheme or host is missing)")

        if parsed.scheme.lower() != "https":
            return ToolResult(
                ok=False,
                error=(
                    "Only https:// is allowed; received "
                    f"{parsed.scheme!r}"
                    ". Report unavailable HTTPS sources to the user."
                ),
            )

        host = parsed.hostname or ""
        if not _host_allowed(host, self._allowed):
            return ToolResult(
                ok=False,
                error=(f"Domain is not allowlisted: {host!r}. Allowed domain suffixes:{sorted(self._allowed)}"),
                recovery_hint=("Use an allowlisted domain or a DOI, PubMed, or arXiv mirror."),
            )

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_s,
                follow_redirects=False,
            ) as client:
                resp = await client.get(url)
        except httpx.TimeoutException as e:
            return ToolResult(
                ok=False,
                error=f"Request timed out after {self._timeout_s}s: {e}",
                recovery_hint="The domain is slow; retry or use another allowlisted mirror.",
            )
        except httpx.HTTPError as e:
            return ToolResult(
                ok=False,
                error=f"HTTP error:{type(e).__name__}: {e}",
            )

        if resp.status_code >= 400:
            return ToolResult(
                ok=False,
                error=(
                    f"HTTP {resp.status_code} from {host!r} (content_length={resp.headers.get('content-length', '?')})"
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

        text = raw.decode("utf-8", errors="replace")
        if truncated:
            text = text + f"\n...[Truncated: original {size_bytes}bytes exceed max_bytes={max_bytes}]"

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
