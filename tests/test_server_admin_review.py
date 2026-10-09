"""M5 admin review API(M9:user_id 来源 query/body → cookie session)。"""

import httpx
import pytest

from praxis2.brains.store import list_brain_docs
from praxis2.memory.extract import ExtractCandidate, persist_candidates
from praxis2.store.base import Namespace
from tests._auth_test_helpers import make_test_app_deps, preseed_session


async def _seed_candidate(store, *, user_id="u1"):
    ns = Namespace(user_id=user_id, scope="review")
    await persist_candidates(
        store,
        ns,
        [ExtractCandidate(id="c1", text="失败经验X doi:10.1/x", trigger="manual")],
    )
    return ns


@pytest.mark.asyncio
async def test_admin_list_pending_returns_candidates():
    from praxis2.server.app import make_app
    from praxis2.store.memory import InMemoryStore

    store = InMemoryStore()
    await _seed_candidate(store)
    deps = make_test_app_deps(store=store)
    # Phase A.1:admin 端点强制 role=='admin'(见 tests/test_security_admin_role.py)
    cookie = await preseed_session(deps, user_id="u1", role="admin")
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get(
            "/admin/review/pending",
            params={"scope": "review"},
            headers={"Cookie": cookie},
        )
        assert r.status_code == 200
        items = r.json()["pending"]
        assert any(i["id"] == "c1" for i in items)
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_admin_approve_promotes_to_brain_and_dequeues():
    from praxis2.server.app import make_app
    from praxis2.store.memory import InMemoryStore

    store = InMemoryStore()
    await _seed_candidate(store)
    deps = make_test_app_deps(store=store)
    cookie = await preseed_session(deps, user_id="u1", role="admin")
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/admin/review/approve",
            json={"scope": "review", "cand_id": "c1", "brain_slug": "Cryo"},
            headers={"Cookie": cookie},
        )
        assert r.status_code == 200
    docs = await list_brain_docs(store, "u1", "Cryo")
    assert any(d.stem == "c1" for d in docs)
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_admin_reject_records_reason():
    from praxis2.server.app import make_app
    from praxis2.store.memory import InMemoryStore

    store = InMemoryStore()
    ns = await _seed_candidate(store)
    deps = make_test_app_deps(store=store)
    cookie = await preseed_session(deps, user_id="u1", role="admin")
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/admin/review/reject",
            json={"scope": "review", "cand_id": "c1", "reason": "证据不足"},
            headers={"Cookie": cookie},
        )
        assert r.status_code == 200
    raw = await store.kv_get(ns, "_reject/c1")
    assert raw is not None and "证据不足" in raw.decode()
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_admin_endpoints_require_cookie_session():
    """§11.6 admin API 同样强制 cookie session(M9:400 → 401)。"""
    from praxis2.server.app import make_app
    from praxis2.store.memory import InMemoryStore

    deps = make_test_app_deps(store=InMemoryStore())
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/admin/review/pending", params={"scope": "review"})
        assert r.status_code == 401
        assert "未登录" in r.text
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_admin_contract_shape_stable_for_frontend():
    from praxis2.server.app import make_app
    from praxis2.store.memory import InMemoryStore

    store = InMemoryStore()
    await _seed_candidate(store)
    deps = make_test_app_deps(store=store)
    cookie = await preseed_session(deps, user_id="u1", role="admin")
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get(
            "/admin/review/pending",
            params={"scope": "review"},
            headers={"Cookie": cookie},
        )
        data = r.json()
        assert set(data.keys()) == {"pending"}
        assert isinstance(data["pending"], list)
        item = data["pending"][0]
        assert {"id", "text", "trigger"} <= set(item.keys())
    await deps.redis.aclose()
