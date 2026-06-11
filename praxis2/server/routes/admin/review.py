"""§7.4.2/S12 管理员审核 API handlers(list_pending/approve/reject)。

路由零业务逻辑:只调 M4/M5 真实 memory/review.{list_pending,approve,
reject}(§2 边界)。契约比照 SSE 不改前端(§5⑥):响应 shape 固定。
§11.6 强制 user_id(无身份是 bug → 400)。审核动作经 review.reject
记因 / approve promote 真实大脑落点(M5 已落,审计 §12)。"""

from praxis2.memory.review import (
    BrainCacheRegistry,
    approve,
    list_pending,
    reject,
)
from praxis2.store.base import Namespace, Store

# 进程级单例:热加载缓存注册表(approve 后失效该 slug,§7.4.2 热加载)
_BRAIN_CACHE = BrainCacheRegistry()


def _ns(user_id: str, scope: str) -> Namespace:
    return Namespace(user_id=user_id, scope=scope)  # 空 user_id 抛(§11.6)


async def handle_admin_list(
    store: Store, *, user_id: str, scope: str
) -> dict:
    pending = await list_pending(store, _ns(user_id, scope))
    return {"pending": pending}  # 契约:顶层只 pending(前端按此消费)


async def handle_admin_approve(
    store: Store, *, user_id: str, scope: str, cand_id: str, brain_slug: str
) -> dict:
    await approve(
        store, _ns(user_id, scope), cand_id,
        brain_slug=brain_slug, cache=_BRAIN_CACHE,
    )
    return {"ok": True, "promoted": cand_id, "brain": brain_slug}


async def handle_admin_reject(
    store: Store, *, user_id: str, scope: str, cand_id: str, reason: str
) -> dict:
    await reject(store, _ns(user_id, scope), cand_id, reason=reason)
    return {"ok": True, "rejected": cand_id}
