

import json
from dataclasses import dataclass

from praxis2.store.base import Namespace, Store

_INDEX_TABLE = "_brain_index"


@dataclass
class BrainDoc:
    slug: str
    kind: str          # cases | neg_cases | rules | skills
    stem: str
    text: str


def brain_ns(user_id: str, slug: str) -> Namespace:
    return Namespace(user_id=user_id, scope=f"brain:{slug}")


def _key(d: BrainDoc) -> str:
    return f"{d.kind}/{d.stem}"


async def put_brain_doc(store: Store, user_id: str, doc: BrainDoc) -> None:
    ns = brain_ns(user_id, doc.slug)
    await store.kv_set(ns, _key(doc), json.dumps(
        {"slug": doc.slug, "kind": doc.kind, "stem": doc.stem, "text": doc.text},
        ensure_ascii=False).encode())
    await store.meta_upsert(_INDEX_TABLE, {
        "user_id": user_id, "pk": f"{doc.slug}/{_key(doc)}",
        "slug": doc.slug, "doc_key": _key(doc)})


async def list_brain_docs(
    store: Store, user_id: str, slug: str
) -> list[BrainDoc]:
    ns = brain_ns(user_id, slug)
    out: list[BrainDoc] = []
    for row in await store.meta_list(_INDEX_TABLE, user_id):
        if row.get("slug") != slug:
            continue
        raw = await store.kv_get(ns, row["doc_key"])
        if raw is None:
            continue
        d = json.loads(raw)
        out.append(BrainDoc(slug=d["slug"], kind=d["kind"],
                            stem=d["stem"], text=d["text"]))
    return out
