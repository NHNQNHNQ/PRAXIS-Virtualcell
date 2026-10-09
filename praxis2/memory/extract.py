import json
from dataclasses import dataclass

from praxis2.store.base import Namespace, Store

CAND_PREFIX = "_candidate/"


@dataclass
class ExtractCandidate:
    id: str
    text: str
    trigger: str  # tool_failure | phase_failure | token_threshold | manual


def extract_candidates(transcript: list[dict], *, trigger: str) -> list[ExtractCandidate]:

    out: list[ExtractCandidate] = []
    n = 0
    for m in transcript:
        c = m.get("content")
        if not isinstance(c, list):
            continue
        for b in c:
            if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                n += 1
                out.append(
                    ExtractCandidate(
                        id=f"{trigger}-{n}",
                        trigger=trigger,
                        text=f"Failure lesson:{b.get('content', '')}",
                    )
                )
    return out


async def persist_candidates(store: Store, ns: Namespace, cands: list[ExtractCandidate]) -> None:

    for c in cands:
        key = CAND_PREFIX + c.id
        if await store.kv_get(ns, key) is not None:
            continue
        await store.kv_set(
            ns, key, json.dumps({"id": c.id, "text": c.text, "trigger": c.trigger}, ensure_ascii=False).encode()
        )
        await store.meta_upsert("_cand_index", {"user_id": ns.user_id, "pk": c.id, "ns_scope": ns.scope})
