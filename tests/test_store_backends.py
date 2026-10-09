import os

import pytest

pytestmark = pytest.mark.integration


async def test_redis_kv_roundtrip():
    from praxis2.store.backends import RedisKVStore
    from praxis2.store.base import Namespace

    s = RedisKVStore(url=os.environ.get("PRAXIS_REDIS_URL", "redis://localhost:6379/0"))
    ns = Namespace(user_id="u1", scope="session")
    await s.kv_set(ns, "k", b"v")
    assert await s.kv_get(ns, "k") == b"v"
    await s.kv_delete(ns, "k")
    assert await s.kv_get(ns, "k") is None
    await s.aclose()


async def test_pg_meta_roundtrip():
    from praxis2.store.backends import PgMetaStore

    s = PgMetaStore(
        dsn=os.environ.get("PRAXIS_PG_DSN", "postgresql://praxis:praxis@localhost:5432/praxis")
    )
    await s.ping()
    await s.aclose()
