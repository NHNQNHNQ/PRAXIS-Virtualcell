"""Retrieve cases, rules, skills, and negative cases from the VirtualCell brain."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from praxis2.brains.migrate import DISCIPLINE_SLUGS, build_fixture_brain, migrate_dir_tree
from praxis2.brains.retrieve import retrieve_brain
from praxis2.tools.base import Tool, ToolResult

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BRAINS_ROOT_DEFAULT = _REPO_ROOT / "brains"


_EXCERPT_MAX_CHARS = 800


def _excerpt(text: str, max_chars: int = _EXCERPT_MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n...[Truncated: original {len(text)}characters]"


class BrainQueryTool(Tool):
    name = "BrainQuery"
    description = (
        "Retrieve relevant cases, rules, skills, and nega"
        "tive cases from a brain. Return document identif"
        "iers and excerpts; set degraded_to_bare=True whe"
        "n nothing matches. Filter kinds with cases, rule"
        "s, skills, and neg_cases."
    )
    rmcp_op = None

    last_retrieval_real_hit = False

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
                "query": {
                    "type": "string",
                    "description": "Retrieval keywords for deterministic keyword ranking",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Return the top k matches, default 5 and maximum 20",
                    "default": 5,
                },
                "kinds": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["cases", "rules", "skills", "neg_cases"],
                    },
                    "description": "Optional document kinds; search all four kinds by default",
                },
            },
            "required": ["brain", "query"],
        }

    async def run(self, payload: dict[str, Any]) -> ToolResult:
        brain = (payload.get("brain") or "").strip().lower()
        query = (payload.get("query") or "").strip()
        top_k = int(payload.get("top_k") or 5)
        top_k = max(1, min(top_k, 20))
        kinds_filter = payload.get("kinds")

        if not brain:
            return ToolResult(
                ok=False,
                error="Missing required brain parameter, for example virtualcell",
                recovery_hint=f"Available brains:{', '.join(DISCIPLINE_SLUGS)}",
            )
        if not query:
            return ToolResult(
                ok=False,
                error="Missing required query parameter",
            )

        brain_dir = self._root / brain
        if not brain_dir.is_dir():
            if brain in DISCIPLINE_SLUGS or brain == "_common":
                docs = build_fixture_brain(brain)
                source = "fixture"
            else:
                return ToolResult(
                    ok=False,
                    error=(
                        f"Unknown brain '{brain}'. Available:{', '.join(DISCIPLINE_SLUGS)}(brains_root={self._root})"
                    ),
                )
        else:
            docs = migrate_dir_tree(brain_dir, brain)
            source = "filesystem"
            if not docs:
                docs = build_fixture_brain(brain)
                source = "fixture(empty real)"

        if kinds_filter:
            allowed = set(kinds_filter)
            docs = [d for d in docs if d.kind in allowed]

        result = retrieve_brain(docs, query, top_k=top_k)

        hits = result.hits
        scores = result.scores or []
        if len(scores) < len(hits):
            scores = list(scores) + [0.0] * (len(hits) - len(scores))
        hits_view = [
            {
                "slug": d.slug,
                "kind": d.kind,
                "stem": d.stem,
                "excerpt": _excerpt(d.text),
                "score": round(float(s), 3),
            }
            for d, s in zip(hits, scores, strict=True)
        ]

        self.last_retrieval_real_hit = source == "filesystem" and not result.degraded_to_bare and bool(hits_view)
        return ToolResult(
            ok=True,
            value={
                "brain": brain,
                "query": query,
                "top_k": top_k,
                "hits": hits_view,
                "degraded_to_bare": result.degraded_to_bare,
                "reason": result.reason,
                "total_docs": len(docs),
                "source": source,
            },
        )
