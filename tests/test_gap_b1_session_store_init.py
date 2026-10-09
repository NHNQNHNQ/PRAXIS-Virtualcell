"""GAP-B-1 Task 1:_App.__init__ 实例化 SessionStore,镜像 ledger/files_repo
的 deps.repo._pool 兜底——无 PG(FakeAuthRepo 无 _pool,测试)→ None,零回归。"""
from __future__ import annotations

import pytest

from praxis2.memory.session import SessionStore
from praxis2.server.app import make_app
from tests._auth_test_helpers import make_test_app_deps


@pytest.mark.asyncio
async def test_no_pg_session_store_is_none():
    """FakeAuthRepository 无 _pool → _session_store=None(退回纯内存态)。"""
    deps = make_test_app_deps()
    app = make_app(deps)
    assert app._app._session_store is None
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_with_pool_session_store_built():
    """deps.repo 有 _pool(模拟 PgAuthRepository)→ 建 SessionStore(deps.store)。"""
    deps = make_test_app_deps()
    deps.repo._pool = object()  # FakeAuthRepository 是普通类,可 setattr
    app = make_app(deps)
    assert isinstance(app._app._session_store, SessionStore)
    await deps.redis.aclose()
