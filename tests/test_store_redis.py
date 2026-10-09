from __future__ import annotations

import pytest

from praxis2.store.base import Namespace


@pytest.mark.asyncio
async def test_redis_store_kv_set_get_delete():
    pytest.importorskip("fakeredis")
    import fakeredis.aioredis

    from praxis2.store.redis import RedisStore

    client = fakeredis.aioredis.FakeRedis()
    st = RedisStore(client)
    ns = Namespace(user_id="u1", scope="cache")
    await st.kv_set(ns, "k1", b"hello")
    assert await st.kv_get(ns, "k1") == b"hello"
    await st.kv_delete(ns, "k1")
    assert await st.kv_get(ns, "k1") is None
    await client.aclose()
