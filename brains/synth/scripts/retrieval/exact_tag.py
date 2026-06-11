"""Generic exact-tag channel for the small categorical fields.

Used for `pathway_class`, `assembly_strategy`, `scale`, `method_choice`. All
behave identically: rank cases whose tag equals the query first, others after.
"""

from __future__ import annotations


def rank_by_field(query_value: str, cases: list[dict], field: str) -> list[str]:
    qv = (query_value or "").strip().lower()
    matches, rest = [], []
    for c in cases:
        cv = (c.get(field) or "").strip().lower()
        if qv and cv and qv == cv:
            matches.append(c["case_id"])
        else:
            rest.append(c["case_id"])
    return matches + rest
