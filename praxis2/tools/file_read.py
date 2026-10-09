"""Read bounded text from allowed repository paths."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from praxis2.tools.base import Tool, ToolResult

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


_ALLOWED_TOPS = {"brains", "docs"}

_DENY_DIRNAMES = {".git", ".venv", "__pycache__", "node_modules", "_audit", ".pytest_cache", ".ruff_cache"}
_EXCERPT_MAX_DEFAULT = 8000


def _looks_binary(b: bytes, sample_size: int = 512) -> bool:
    sample = b[:sample_size]
    if b"\x00" in sample:
        return True

    nontext = sum(1 for c in sample if c < 9 or (13 < c < 32))
    return len(sample) > 0 and nontext / len(sample) > 0.3


class FileReadTool(Tool):
    name = "FileRead"
    description = (
        "Read bounded text from allowlisted brains/ and d"
        "ocs/ repository paths. Absolute paths, escapes, "
        "and internal directories are denied. Binary file"
        "s are marked; max_chars defaults to 8000."
    )
    rmcp_op = None

    def __init__(self, repo_root: Path | None = None) -> None:
        self._root = Path(repo_root) if repo_root else _REPO_ROOT

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": ("Repository-relative path under brains/ or docs/, for example docs/USER-GUIDE.md"),
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum returned characters, default 8000 and greater than zero",
                    "default": _EXCERPT_MAX_DEFAULT,
                },
            },
            "required": ["path"],
        }

    async def run(self, payload: dict[str, Any]) -> ToolResult:
        raw_path = (payload.get("path") or "").strip()
        max_chars = int(payload.get("max_chars") or _EXCERPT_MAX_DEFAULT)
        max_chars = max(100, min(max_chars, 100_000))

        if not raw_path:
            return ToolResult(ok=False, error="Missing required path")

        p_input = Path(raw_path)
        if p_input.is_absolute():
            return ToolResult(
                ok=False,
                error=f"Absolute paths are denied: {raw_path!r}(repository-relative paths only)",
            )

        abs_path = (self._root / p_input).resolve()
        try:
            rel = abs_path.relative_to(self._root.resolve())
        except ValueError:
            return ToolResult(
                ok=False,
                error=(f"Path escape denied:{raw_path!r}resolves outside repository {self._root} (escape detected)"),
            )

        parts = rel.parts

        if not parts or parts[0] not in _ALLOWED_TOPS:
            return ToolResult(
                ok=False,
                error=(
                    f"Path is not allowlisted: {raw_path!r}. Allowed top-level directories:{sorted(_ALLOWED_TOPS)}"
                    "(allowed tops only)"
                ),
            )

        for seg in parts:
            if seg in _DENY_DIRNAMES:
                return ToolResult(
                    ok=False,
                    error=f"Denylisted directory: {raw_path!r}(matched {seg!r}, blacklist)",
                )

        if not abs_path.exists():
            return ToolResult(
                ok=False,
                error=f"Path does not exist: {raw_path!r}(not found)",
            )
        if abs_path.is_dir():
            return ToolResult(
                ok=False,
                error=f"Path is a directory: {raw_path!r}(use a listing tool or provide an exact filename)",
            )

        raw_bytes = abs_path.read_bytes()
        size_bytes = len(raw_bytes)
        is_binary = _looks_binary(raw_bytes)
        if is_binary:
            return ToolResult(
                ok=True,
                value={
                    "path": str(rel),
                    "size_bytes": size_bytes,
                    "is_binary": True,
                    "content": f"[Binary file,{size_bytes}bytes; content omitted]",
                    "truncated": False,
                },
            )

        text = raw_bytes.decode("utf-8", errors="replace")
        full_len = len(text)
        truncated = full_len > max_chars
        if truncated:
            text = text[:max_chars] + f"\n...[Truncated: original {full_len}characters exceed max_chars={max_chars}]"

        return ToolResult(
            ok=True,
            value={
                "path": str(rel),
                "size_bytes": size_bytes,
                "is_binary": False,
                "content": text,
                "truncated": truncated,
                "max_chars": max_chars,
            },
        )
