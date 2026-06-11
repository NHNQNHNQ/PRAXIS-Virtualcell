"""FileReadTool:模型可调用的"读 repo 内安全路径"工具(v0.16.0-beta P0 3/5)。

回归:此前模型在 chat 里想"看看 brains/<slug>/skills/workflows/<name>/SKILL.md
怎么写的"只能问用户复制粘贴 — 没有工具能读 repo 内文件。本工具补这一缝。

沙盒(v0.16.0-beta):
- 仅允许 brains/ + docs/ 两个顶层(repo 内,所有用户共享)
- 黑名单子目录:.git/.venv/__pycache__/node_modules/_audit
- 绝对路径 / ../ 越权 → 拒绝
- 文件大小上限:max_chars(默认 8000,截断+标记)

后续 v0.18 跨会话记忆时接入 user storage(每用户独立)+ 远端 .53 user data。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from praxis2.tools.base import Tool, ToolResult

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# 白名单顶层目录(repo 相对路径首段必须命中)
_ALLOWED_TOPS = {"brains", "docs"}
# 黑名单子目录名(路径任何一段命中即拒)
_DENY_DIRNAMES = {".git", ".venv", "__pycache__", "node_modules", "_audit", ".pytest_cache", ".ruff_cache"}
_EXCERPT_MAX_DEFAULT = 8000


def _looks_binary(b: bytes, sample_size: int = 512) -> bool:
    sample = b[:sample_size]
    if b"\x00" in sample:
        return True
    # 简易启发:非可打印字符比例 > 30%
    nontext = sum(1 for c in sample if c < 9 or (13 < c < 32))
    return len(sample) > 0 and nontext / len(sample) > 0.3


class FileReadTool(Tool):
    """读 repo 内白名单路径(brains/ + docs/)文件。"""

    name = "FileRead"
    description = (
        "读 repo 内白名单路径(brains/ + docs/)的文本文件,用于查看 SKILL.md / "
        "case markdown / 路线图文档等。沙盒:绝对路径 / ../ 越权拒;.git/.venv/"
        "__pycache__ 等黑名单拒;binary 标记 + size cap(max_chars 默认 8000)。"
    )
    rmcp_op = None  # 读类不受相位门约束

    def __init__(self, repo_root: Path | None = None) -> None:
        self._root = Path(repo_root) if repo_root else _REPO_ROOT

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "repo 相对路径(必须以 brains/ 或 docs/ 开头),"
                        "例: brains/enzyme/memory/cases/c1.md / docs/test-plans/2026-06-01-next-steps.md"
                    ),
                },
                "max_chars": {
                    "type": "integer",
                    "description": "返回内容上限字符数(默认 8000,>0)",
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
            return ToolResult(ok=False, error="缺 path(必填)")

        # 1) 绝对路径拒
        p_input = Path(raw_path)
        if p_input.is_absolute():
            return ToolResult(
                ok=False,
                error=f"沙盒拒绝绝对路径 {raw_path!r}(仅允许 repo 相对路径)",
            )

        # 2) 拼出真实 abs path,resolve 后必须仍在 repo 内(防 ../ 越权)
        abs_path = (self._root / p_input).resolve()
        try:
            rel = abs_path.relative_to(self._root.resolve())
        except ValueError:
            return ToolResult(
                ok=False,
                error=(
                    f"沙盒越权拒绝:{raw_path!r} resolve 后在 repo {self._root} 外"
                    f"(escape detected)"
                ),
            )

        parts = rel.parts
        # 3) 白名单顶层
        if not parts or parts[0] not in _ALLOWED_TOPS:
            return ToolResult(
                ok=False,
                error=(
                    f"非白名单路径 {raw_path!r}。白名单顶层:{sorted(_ALLOWED_TOPS)}"
                    "(allowed tops only)"
                ),
            )
        # 4) 黑名单子目录(任何一段)
        for seg in parts:
            if seg in _DENY_DIRNAMES:
                return ToolResult(
                    ok=False,
                    error=f"黑名单目录拒绝 {raw_path!r}(命中 {seg!r}, blacklist)",
                )

        # 5) 存在性 / 文件性
        if not abs_path.exists():
            return ToolResult(
                ok=False,
                error=f"路径不存在 {raw_path!r}(not found)",
            )
        if abs_path.is_dir():
            return ToolResult(
                ok=False,
                error=f"路径是目录而非文件 {raw_path!r}(directory not allowed,改用 listing 工具或精确文件名)",
            )

        # 6) 读 + binary 检测 + 截断
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
                    "content": f"[二进制文件,{size_bytes} bytes,不返回正文]",
                    "truncated": False,
                },
            )

        text = raw_bytes.decode("utf-8", errors="replace")
        full_len = len(text)  # v0.16.3:复用已 decode 的 text,不再重复 decode
        truncated = full_len > max_chars
        if truncated:
            text = text[:max_chars] + f"\n…[截断:原 {full_len} 字符超 max_chars={max_chars}]"

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
