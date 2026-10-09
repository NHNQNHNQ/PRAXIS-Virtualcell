"""Rank brain documents with deterministic keyword relevance."""

import re
from dataclasses import dataclass, field
from typing import Any


_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+")


def _tokens(s: str) -> list[str]:
    return _TOKEN_RE.findall(s.lower())


@dataclass
class RetrievalResult:
    hits: list[Any]
    degraded_to_bare: bool
    reason: str = ""
    scores: list[float] = field(default_factory=list)


def retrieve_brain(docs: list[Any], query: str, *, top_k: int) -> RetrievalResult:

    q = set(_tokens(query))
    if not docs or not q:
        return RetrievalResult(
            hits=[], degraded_to_bare=True,
            reason="No documents or an empty query; explicitly fall back to bare mode",
        )
    scored: list[tuple[float, Any]] = []
    for d in docs:
        toks = _tokens(getattr(d, "text", ""))
        if not toks:
            continue
        tf = sum(toks.count(w) for w in q)
        if tf <= 0:
            continue
        score = tf / (1.0 + 0.001 * len(toks))
        scored.append((score, d))
    if not scored:
        return RetrievalResult(
            hits=[], degraded_to_bare=True,
            reason="No retrieval matches; explicitly fall back to bare mode without domain evidence",
        )
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]
    return RetrievalResult(
        hits=[d for _, d in top], degraded_to_bare=False,
        scores=[s for s, _ in top],
    )
