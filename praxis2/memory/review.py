import json

from praxis2.brains.store import BrainDoc, put_brain_doc
from praxis2.memory.extract import CAND_PREFIX
from praxis2.store.base import Namespace, Store


class BrainCacheRegistry:
    def __init__(self) -> None:
        self._loaded: set[str] = set()
        self._versions: dict[str, int] = {}

    def mark_loaded(self, slug: str) -> None:
        self._loaded.add(slug)

    def is_loaded(self, slug: str) -> bool:
        return slug in self._loaded

    def invalidate(self, slug: str) -> None:

        self._loaded.discard(slug)
        self._versions[slug] = self._versions.get(slug, 0) + 1

    def bump(self, slug: str) -> int:

        self._versions[slug] = self._versions.get(slug, 0) + 1
        self._loaded.discard(slug)
        return self._versions[slug]

    def version(self, slug: str) -> int:

        return self._versions.get(slug, 0)


async def list_pending(store: Store, ns: Namespace) -> list[dict]:
    out = []
    for row in await store.meta_list("_cand_index", ns.user_id):
        if row.get("ns_scope") == ns.scope:
            raw = await store.kv_get(ns, CAND_PREFIX + row["pk"])
            if raw is not None:
                out.append(json.loads(raw))
    return out


async def _dequeue(store: Store, ns: Namespace, cand_id: str) -> dict | None:
    raw = await store.kv_get(ns, CAND_PREFIX + cand_id)
    if raw is None:
        return None
    await store.kv_delete(ns, CAND_PREFIX + cand_id)
    return json.loads(raw)


async def approve(
    store: Store,
    ns: Namespace,
    cand_id: str,
    *,
    brain_slug: str,
    cache: BrainCacheRegistry | None = None,
) -> None:

    if not brain_slug or not cand_id:
        raise ValueError("approve: brain_slug and cand_id must not be empty")
    c = await _dequeue(store, ns, cand_id)
    if c is None:
        return
    doc = BrainDoc(
        slug=brain_slug,
        kind="cases",
        stem=cand_id,
        text=str(c.get("text", "")),
    )

    if cache is not None:
        cache.bump(brain_slug)
    await put_brain_doc(store, ns.user_id, doc)


async def reject(store: Store, ns: Namespace, cand_id: str, *, reason: str) -> None:

    c = await _dequeue(store, ns, cand_id)
    if c is None:
        return
    await store.kv_set(
        ns, f"_reject/{cand_id}", json.dumps({"id": cand_id, "reason": reason}, ensure_ascii=False).encode()
    )
