"""Write cited candidate cases to a local brain review inbox."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from praxis2.brains.migrate import DISCIPLINE_SLUGS
from praxis2.tools.base import Tool, ToolResult

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BRAINS_ROOT_DEFAULT = _REPO_ROOT / "brains"


_STEM_UNSAFE = re.compile(r"[^A-Za-z0-9_\-]+")


def _safe_stem(title: str, *, max_len: int = 80) -> str:

    s = _STEM_UNSAFE.sub("-", title.strip()).strip("-")
    s = re.sub(r"-+", "-", s)
    if not s:
        s = "untitled"
    return s[:max_len].rstrip("-") or "untitled"


def _format_doi_field(doi: str) -> str:

    if "/" in doi or ":" in doi:
        return f'"{doi}"'
    return doi


def _render_markdown(*, brain: str, title: str, summary: str, evidence: list[dict]) -> str:
    primary_doi = evidence[0].get("doi", "") if evidence else ""
    lines = [
        "---",
        f"case_id: {_safe_stem(title)}",
        f"brain: {brain}",
        "status: proposed",
        f"title: {title!r}",
        f"doi: {_format_doi_field(primary_doi)}" if primary_doi else "doi: null",
        f"evidence_count: {len(evidence)}",
        "schema_version: 1",
        "---",
        "",
        f"# {title}",
        "",
        "## Summary",
        "",
        summary.strip(),
        "",
        "## Evidence",
        "",
    ]
    if not evidence:
        lines.append("(none)")
    else:
        for i, ev in enumerate(evidence, 1):
            doi = ev.get("doi", "(no DOI)")
            citation = ev.get("citation", "")
            note = ev.get("note", "")
            lines.append(f"{i}. DOI: `{doi}`")
            if citation:
                lines.append(f"   - Citation:{citation}")
            if note:
                lines.append(f"   - Note:{note}")
    lines.append("")
    return "\n".join(lines)


class RMCPWriteCaseTool(Tool):
    name = "RMCPWriteCase"
    description = (
        "Write a candidate case to the local brain _propo"
        "sed inbox for review. Supply brain, title, summa"
        "ry, and evidence containing a DOI. Repeated titl"
        "es overwrite their candidate case."
    )

    rmcp_op = "write_case"

    def __init__(self, brains_root: Path | None = None) -> None:
        self._root = Path(brains_root) if brains_root else _BRAINS_ROOT_DEFAULT

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "brain": {
                    "type": "string",
                    "description": ("Lowercase brain identifier, such as virtualcell"),
                },
                "title": {
                    "type": "string",
                    "description": "Human-readable case title; repeated titles overwrite the candidate",
                },
                "summary": {
                    "type": "string",
                    "description": "Case summary in Markdown, with conclusions and source references",
                },
                "evidence": {
                    "type": "array",
                    "description": (
                        "Evidence entries with doi, optional citation and note; at least one DOI is required"
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "doi": {"type": "string"},
                            "citation": {"type": "string"},
                            "note": {"type": "string"},
                        },
                        "required": ["doi"],
                    },
                },
            },
            "required": ["brain", "title", "summary", "evidence"],
        }

    async def run(self, payload: dict[str, Any]) -> ToolResult:
        brain = (payload.get("brain") or "").strip().lower()
        title = (payload.get("title") or "").strip()
        summary = (payload.get("summary") or "").strip()
        evidence = payload.get("evidence") or []

        if not brain:
            return ToolResult(ok=False, error="Missing required brain, for example virtualcell")
        if not title:
            return ToolResult(ok=False, error="Missing required title")
        if not summary:
            return ToolResult(ok=False, error="Missing required summary")
        if not isinstance(evidence, list) or not evidence:
            return ToolResult(
                ok=False,
                error=("evidence must be a nonempty list containing at least one DOI"),
                recovery_hint=('evidence=[{"doi": "10.XXX/YYY", "citation": "Author Year Journal"}]'),
            )

        dois = [str(ev.get("doi") or "").strip() for ev in evidence if isinstance(ev, dict)]
        if not any(dois):
            return ToolResult(
                ok=False,
                error=("At least one evidence entry must have a nonempty doi field"),
            )

        if brain not in DISCIPLINE_SLUGS and brain != "_common":
            return ToolResult(
                ok=False,
                error=(f"Unknown brain '{brain}'. Available:{', '.join(DISCIPLINE_SLUGS)}"),
            )

        inbox = self._root / brain / "memory" / "cases" / "_proposed"
        stem = _safe_stem(title)
        path = inbox / f"{stem}.md"
        content = _render_markdown(
            brain=brain,
            title=title,
            summary=summary,
            evidence=evidence,
        )
        try:
            inbox.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError as e:
            return ToolResult(
                ok=False,
                error=(
                    "Could not write candidate case ("
                    f"{type(e).__name__}"
                    ": "
                    f"{e}"
                    "). Target "
                    f"{inbox}"
                    "may lack write permission, be read-only, or have"
                    " no free disk space."
                ),
                recovery_hint="Check write access to brains_root.",
            )

        try:
            rel = path.relative_to(_REPO_ROOT)
            rel_str = str(rel)
        except ValueError:
            rel_str = str(path)

        return ToolResult(
            ok=True,
            value={
                "brain": brain,
                "title": title,
                "stem": stem,
                "written_path": str(path),
                "written_path_rel": rel_str,
                "evidence_count": len(evidence),
                "status": "proposed (review inbox)",
                "next_action": (
                    f"Candidate case written to {rel_str}; review it before moving it into accepted cases."
                ),
            },
        )
