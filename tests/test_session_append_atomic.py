import asyncio

import pytest

from praxis2.memory.session import SessionEntry, SessionStore
from praxis2.store.base import Namespace
from praxis2.store.memory import InMemoryStore


def _entry(idx: int, *, user_id: str = "u1", session_id: str = "s1") -> SessionEntry:
    return SessionEntry(
        uuid=f"e{idx}",
        type="user",
        content=f"msg {idx}",
        user_id=user_id,
        session_id=session_id,
    )


@pytest.mark.asyncio
async def test_append_blob_size_is_linear_not_quadratic():

    store = InMemoryStore()
    ss = SessionStore(store)
    n = 1000
    for i in range(n):
        await ss.append_entry(_entry(i))
    ns = Namespace(user_id="u1", scope="transcript")
    blob = await store.blob_get(ns, "s1")
    assert blob is not None

    lines = [ln for ln in blob.decode("utf-8").splitlines() if ln.strip()]
    assert len(lines) == n

    assert len(blob) < n * 500, f"Observed {len(blob)} bytes; quadratic transcript growth is not acceptable"


@pytest.mark.asyncio
async def test_concurrent_append_no_loss():

    store = InMemoryStore()
    ss = SessionStore(store)
    n = 50
    entries = [_entry(i) for i in range(n)]
    await asyncio.gather(*(ss.append_entry(e) for e in entries))
    seq = await ss.load_transcript(user_id="u1", session_id="s1")
    uuids = {e.uuid for e in seq}
    assert len(uuids) == n, f"Lost entries: expected {n} UUIDs; observed {len(uuids)}"


@pytest.mark.asyncio
async def test_uuid_dedup_on_read_side():

    store = InMemoryStore()
    ss = SessionStore(store)
    e_first = SessionEntry(
        uuid="dup",
        type="user",
        content="first",
        user_id="u1",
        session_id="s1",
    )
    e_dup = SessionEntry(
        uuid="dup",
        type="user",
        content="dup-should-be-ignored",
        user_id="u1",
        session_id="s1",
    )
    await ss.append_entry(e_first)
    await ss.append_entry(e_dup)
    seq = await ss.load_transcript(user_id="u1", session_id="s1")
    assert len(seq) == 1
    assert seq[0].content == "first"


@pytest.mark.asyncio
async def test_inmemory_blob_append_basic():

    store = InMemoryStore()
    ns = Namespace(user_id="u1", scope="transcript")
    await store.blob_append(ns, "k", b"hello\n")
    await store.blob_append(ns, "k", b"world\n")
    assert await store.blob_get(ns, "k") == b"hello\nworld\n"


@pytest.mark.asyncio
async def test_inmemory_blob_append_creates_when_missing():

    store = InMemoryStore()
    ns = Namespace(user_id="u1", scope="transcript")
    await store.blob_append(ns, "new", b"chunk1")
    assert await store.blob_get(ns, "new") == b"chunk1"


@pytest.mark.asyncio
async def test_redis_blob_append_raises_not_implemented():

    pytest.importorskip("fakeredis")
    import fakeredis.aioredis

    from praxis2.store.redis import RedisStore

    client = fakeredis.aioredis.FakeRedis()
    st = RedisStore(client)
    ns = Namespace(user_id="u1", scope="transcript")
    with pytest.raises(NotImplementedError):
        await st.blob_append(ns, "k", b"x")
    await client.aclose()
