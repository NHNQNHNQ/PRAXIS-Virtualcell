"""Phase A.1 / reviewer M9 C1:admin review 端点必须强制 role == 'admin'。

回归点:
- 无 cookie    → 401(原有 §11.6 行为,锁住不回归;fixup 后 schema 统一)
- role=user    → 403(本次新增校验)+ handler 副作用未执行(I2 防回归)
- role=admin   → 非 403(放行,200 或业务路径)

覆盖三条 admin 路由:/admin/review/pending(GET)/ approve(POST)/ reject(POST)。

错误响应 schema 统一(fixup I1):
  {"error": "<short_code>", "reason": "<human_readable>"}
  - 401:error="unauthorized"
  - 403:error="forbidden"
"""

from __future__ import annotations

import httpx
import pytest

from praxis2.memory.extract import ExtractCandidate, persist_candidates
from praxis2.memory.review import list_pending
from praxis2.store.base import Namespace
from praxis2.store.memory import InMemoryStore
from tests._auth_test_helpers import make_test_app_deps, preseed_session


async def _seed_candidate(store, *, user_id="u1"):
    ns = Namespace(user_id=user_id, scope="review")
    await persist_candidates(
        store,
        ns,
        [ExtractCandidate(id="c1", text="text doi:10.1/x", trigger="manual")],
    )
    return ns


# ---------- role=user 必须 403 ----------


@pytest.mark.asyncio
async def test_user_role_cannot_list_admin_review():
    from praxis2.server.app import make_app

    store = InMemoryStore()
    await _seed_candidate(store)
    deps = make_test_app_deps(store=store)
    cookie = await preseed_session(deps, user_id="u1", role="user")
    app = make_app(deps)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.get(
            "/admin/review/pending",
            params={"scope": "review"},
            headers={"Cookie": cookie},
        )
        assert r.status_code == 403, r.text
        assert "admin" in r.text.lower()
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_user_role_cannot_approve():
    from praxis2.server.app import make_app

    store = InMemoryStore()
    ns = await _seed_candidate(store)
    deps = make_test_app_deps(store=store)
    cookie = await preseed_session(deps, user_id="u1", role="user")
    app = make_app(deps)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(
            "/admin/review/approve",
            json={"scope": "review", "cand_id": "c1", "brain_slug": "Cryo"},
            headers={"Cookie": cookie},
        )
        assert r.status_code == 403, r.text
        # I2 副作用防回归:403 拦截后 candidate 必须仍在 review 队列,
        # 未被 dequeue / promote 到 brain ns
        pending = await list_pending(store, ns)
        assert any(p.get("id") == "c1" for p in pending), \
            "403 不应触发 approve 副作用(candidate 必须仍在 review 队列)"
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_user_role_cannot_reject():
    from praxis2.server.app import make_app

    store = InMemoryStore()
    ns = await _seed_candidate(store)
    deps = make_test_app_deps(store=store)
    cookie = await preseed_session(deps, user_id="u1", role="user")
    app = make_app(deps)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(
            "/admin/review/reject",
            json={"scope": "review", "cand_id": "c1", "reason": "证据不足"},
            headers={"Cookie": cookie},
        )
        assert r.status_code == 403, r.text
        # I2 副作用防回归:403 拦截后 candidate 必须仍在 review 队列,
        # 未被 dequeue 或写 _reject/{cand_id}
        pending = await list_pending(store, ns)
        assert any(p.get("id") == "c1" for p in pending), \
            "403 不应触发 reject 副作用(candidate 必须仍在 review 队列)"
        # 同时确认无 reject 记录写入
        reject_raw = await store.kv_get(ns, "_reject/c1")
        assert reject_raw is None, "403 不应写 _reject 记录"
    await deps.redis.aclose()


# ---------- role=admin 必须放行(非 403)----------


@pytest.mark.asyncio
async def test_admin_role_can_list():
    from praxis2.server.app import make_app

    store = InMemoryStore()
    await _seed_candidate(store)
    deps = make_test_app_deps(store=store)
    cookie = await preseed_session(deps, user_id="u1", role="admin")
    app = make_app(deps)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.get(
            "/admin/review/pending",
            params={"scope": "review"},
            headers={"Cookie": cookie},
        )
        assert r.status_code == 200, r.text
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_admin_role_can_approve():
    from praxis2.server.app import make_app

    store = InMemoryStore()
    await _seed_candidate(store)
    deps = make_test_app_deps(store=store)
    cookie = await preseed_session(deps, user_id="u1", role="admin")
    app = make_app(deps)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(
            "/admin/review/approve",
            json={"scope": "review", "cand_id": "c1", "brain_slug": "Cryo"},
            headers={"Cookie": cookie},
        )
        assert r.status_code != 403, r.text
        assert r.status_code == 200, r.text
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_admin_role_can_reject():
    from praxis2.server.app import make_app

    store = InMemoryStore()
    await _seed_candidate(store)
    deps = make_test_app_deps(store=store)
    cookie = await preseed_session(deps, user_id="u1", role="admin")
    app = make_app(deps)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(
            "/admin/review/reject",
            json={"scope": "review", "cand_id": "c1", "reason": "证据不足"},
            headers={"Cookie": cookie},
        )
        assert r.status_code != 403, r.text
        assert r.status_code == 200, r.text
    await deps.redis.aclose()


# ---------- 无 cookie 仍 401(锁既有行为)----------


@pytest.mark.asyncio
async def test_no_cookie_returns_401_not_403():
    from praxis2.server.app import make_app

    deps = make_test_app_deps(store=InMemoryStore())
    app = make_app(deps)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.get("/admin/review/pending", params={"scope": "review"})
        assert r.status_code == 401, r.text
        # I1 schema 统一:{"error": "unauthorized", "reason": "..."}
        body = r.json()
        assert body.get("error") == "unauthorized", body
        assert "reason" in body, body
        assert "未登录" in body["reason"], body

        r = await c.post(
            "/admin/review/approve",
            json={"scope": "review", "cand_id": "c1", "brain_slug": "Cryo"},
        )
        assert r.status_code == 401, r.text
        body = r.json()
        assert body.get("error") == "unauthorized", body
        assert "reason" in body, body

        r = await c.post(
            "/admin/review/reject",
            json={"scope": "review", "cand_id": "c1", "reason": "x"},
        )
        assert r.status_code == 401, r.text
        body = r.json()
        assert body.get("error") == "unauthorized", body
        assert "reason" in body, body
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_user_role_403_body_has_short_code_and_reason():
    """I1 schema 统一:403 body 也必须是 {"error": "forbidden", "reason": "..."}。"""
    from praxis2.server.app import make_app

    store = InMemoryStore()
    await _seed_candidate(store)
    deps = make_test_app_deps(store=store)
    cookie = await preseed_session(deps, user_id="u1", role="user")
    app = make_app(deps)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.get(
            "/admin/review/pending",
            params={"scope": "review"},
            headers={"Cookie": cookie},
        )
        assert r.status_code == 403, r.text
        body = r.json()
        assert body.get("error") == "forbidden", body
        assert body.get("reason") == "admin only", body
    await deps.redis.aclose()
