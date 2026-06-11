"""候选审核(总纲 §7.4.2)。M5 增强:approve promote 真实落点
brains/<slug>(经 brains/store)+ 热加载(BrainCacheRegistry 失效)。
保持 M4 approve/reject/list_pending 签名兼容(零回归)。

管理员审核 API(server/routes/admin/,比照 SSE 契约不改前端)留 M6
(总纲 §7.4.2 已校准,路线图已回写)。审核动作全程审计(§12)。"""

import json

from praxis2.brains.store import BrainDoc, put_brain_doc
from praxis2.memory.extract import CAND_PREFIX
from praxis2.store.base import Namespace, Store


class BrainCacheRegistry:
    """热加载支撑:记录哪些大脑已被加载进检索缓存;approve 后失效该 slug,
    下次 list_brain_docs/检索读到 promote 的新内容(§7.4.2 热加载)。
    M5 内存态;真后端缓存(Redis)接入 M6/M7。

    D.7(reviewer M5 #3):增 version 计数 + 显式 bump API,支持
    invalidate-before-put 反竞态序。窗口期内并发 retriever 见 version 增,
    应主动重读 store,而非复用 cached docs(避免 stale-after-cleared-flag)。
    invalidate(slug) 旧 API 保持:discard loaded + bump version,
    M4/M5 既有调用方零破坏。"""

    def __init__(self) -> None:
        self._loaded: set[str] = set()
        self._versions: dict[str, int] = {}

    def mark_loaded(self, slug: str) -> None:
        self._loaded.add(slug)

    def is_loaded(self, slug: str) -> bool:
        return slug in self._loaded

    def invalidate(self, slug: str) -> None:
        """旧 API 兼容:= bump version + discard loaded mark(语义合并)。"""
        self._loaded.discard(slug)
        self._versions[slug] = self._versions.get(slug, 0) + 1

    def bump(self, slug: str) -> int:
        """显式 bump version(invalidate-before-put 路径用)。
        approve 流程:bump → put_brain_doc;并发 retriever 见 version 已增,
        主动重读 store。返回新 version。"""
        self._versions[slug] = self._versions.get(slug, 0) + 1
        self._loaded.discard(slug)
        return self._versions[slug]

    def version(self, slug: str) -> int:
        """读 slug 当前 version(未见过的 slug 返回 0,默认值语义)。"""
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
    """approve → promote 到真实大脑落点 brains/<slug>(经 brains/store,
    M5 让 M4 前置接口成真)+ 出队 + 触发热加载(失效检索缓存)。
    M4 签名兼容:cache 为新增可选 keyword-only 参数,不传时仅 promote。
    text 缺失时 promote 空文本(上游 ExtractCandidate 保证非空)。"""
    # fail-fast 须在 _dequeue 之前:空 slug/id 会让 put_brain_doc 的
    # meta_upsert 抛 ValueError,若已出队则候选静默丢失(数据丢失)
    if not brain_slug or not cand_id:
        raise ValueError("approve:brain_slug 与 cand_id 不得为空")
    c = await _dequeue(store, ns, cand_id)
    if c is None:
        return
    doc = BrainDoc(
        slug=brain_slug, kind="cases", stem=cand_id,
        text=str(c.get("text", "")),
    )
    # D.7(reviewer M5 #3):invalidate-before-put — 先 bump version,再写大脑。
    # 旧序(put → invalidate)留窗口期:并发 retriever 见 is_loaded=True
    # 复用 cached 旧 docs(stale)。新序:bump 早于 put,窗口期内 retriever
    # 见 version 已增,主动重读 store(读到当前版本,非完美原子但非 stale)。
    # 真原子需 store 层 lock(M6/M7 Redis 真后端 follow-up),本 task 留接口。
    if cache is not None:
        cache.bump(brain_slug)
    await put_brain_doc(store, ns.user_id, doc)


async def reject(store: Store, ns: Namespace, cand_id: str, *, reason: str) -> None:
    """reject → 出队 + 记因审计(§12)。"""
    c = await _dequeue(store, ns, cand_id)
    if c is None:
        return
    await store.kv_set(ns, f"_reject/{cand_id}", json.dumps(
        {"id": cand_id, "reason": reason}, ensure_ascii=False).encode())
