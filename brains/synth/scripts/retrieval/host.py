"""host_organism channel — exact-tag with synonym table.

Loads the synonym table from memory/index.json::host_synonyms and matches by
canonical genus or by membership in a synonym group.
"""

from __future__ import annotations

import json
from pathlib import Path


def _load_synonyms(index_path: Path) -> dict[str, set[str]]:
    if not index_path.exists():
        return {}
    try:
        d = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    table = d.get("host_synonyms") or {}
    out: dict[str, set[str]] = {}
    for canonical, syns in table.items():
        group = {canonical.lower(), *(s.lower() for s in syns)}
        out[canonical] = group
    return out


def _canonical_for(name: str, synonyms: dict[str, set[str]]) -> str | None:
    n = (name or "").lower().strip()
    if not n:
        return None
    for canonical, group in synonyms.items():
        if any(g in n or n in g for g in group):
            return canonical
    # Genus-only fallback: take first word
    first = n.split()[0]
    for canonical in synonyms:
        if canonical.lower().split()[0] == first:
            return canonical
    return None


def rank_by_host(query_host: str, cases: list[dict], index_path: Path) -> list[str]:
    """Return case_ids ordered: same canonical host first, then everything else."""
    synonyms = _load_synonyms(index_path)
    canon_q = _canonical_for(query_host, synonyms)
    ranked = []
    rest = []
    for c in cases:
        h = c.get("host_organism") or c.get("target_host") or ""
        canon_c = _canonical_for(h, synonyms)
        if canon_q and canon_c and canon_q == canon_c:
            ranked.append(c["case_id"])
        else:
            rest.append(c["case_id"])
    return ranked + rest
