"""brains 经 store 抽象(scope=brain:<slug>,总纲 §7.4.2/§11.6)。
对齐 M4 memory/review.py approve 已写的 Namespace(user_id, scope=
f"brain:{brain_slug}") 前置接口——M5 让它成真实大脑落点。

强制 user_id 命名空间(§11.6):brain_ns 直接构造 Namespace,空 user_id
由 Namespace.__post_init__ 抛 ValueError。"""

import json
from dataclasses import dataclass

from praxis2.store.base import Namespace, Store

_INDEX_TABLE = "_brain_index"


@dataclass
class BrainDoc:
    slug: str          # _common | general | <13 学科>
    kind: str          # cases | neg_cases | rules | skills
    stem: str          # 文件 stem(合并按 stem 覆盖,v1 §2.1)
    text: str          # 正文(skills 类为目录名/SKILL.md 摘要)


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
