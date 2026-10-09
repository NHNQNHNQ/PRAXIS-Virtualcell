"""C.3(reviewer M1 C1):SessionStore.append_entry 改 O(1) 单条原子,并发不丢。

原实现:每次 append = load 全盘 + dedup + 序列化 + put 整盘 → O(K²) 读写;
read-modify-write 非原子 → 并发 append 互相覆盖,丢条目。
本组测试锁死新契约:
1. blob 大小线性 ≈ O(K),不是 O(K²)。
2. 50 个并发 append 同 session,最终 transcript 含全部 50 个 unique entry。
3. 重复 UUID 写两次 → load_transcript 读侧去重,只看到一次(行为对外不变)。
"""

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
    """1000 个 append 后,blob 大小应线性累加(O(K)),不是 O(K²) 重写整盘。

    每 entry serialized ≈ 130 bytes(uuid + 字段 + json),1000 条 ≈ 130KB。
    若仍是 O(K²) read-modify-write,实际 blob 会一直被重写,
    但最终 blob 大小仍是 O(K)——这里我们额外验证 InMemoryStore 内部 blob
    确实"逐条累加"(=newline-delimited 行数 = N)。
    """
    store = InMemoryStore()
    ss = SessionStore(store)
    n = 1000
    for i in range(n):
        await ss.append_entry(_entry(i))
    ns = Namespace(user_id="u1", scope="transcript")
    blob = await store.blob_get(ns, "s1")
    assert blob is not None
    # 行数 = 写入条数(append-only,O(K))
    lines = [ln for ln in blob.decode("utf-8").splitlines() if ln.strip()]
    assert len(lines) == n
    # 体量上界(单条 ≈ 200 bytes 充足上界)
    assert len(blob) < n * 500, f"实际 {len(blob)} bytes,O(K²) 会爆"


@pytest.mark.asyncio
async def test_concurrent_append_no_loss():
    """50 个并发 append 同 session,最终 transcript 应含全部 50 个 unique entry。

    原 read-modify-write 实现:每个协程独立 load → 看不到对方写入 → 各自 put
    整盘 → 互相覆盖 → 丢条目。新 blob_append 原子追加 → 0 丢失。
    """
    store = InMemoryStore()
    ss = SessionStore(store)
    n = 50
    entries = [_entry(i) for i in range(n)]
    await asyncio.gather(*(ss.append_entry(e) for e in entries))
    seq = await ss.load_transcript(user_id="u1", session_id="s1")
    uuids = {e.uuid for e in seq}
    assert len(uuids) == n, f"丢条目:期望 {n} 个 uuid,实际 {len(uuids)}"


@pytest.mark.asyncio
async def test_uuid_dedup_on_read_side():
    """重复 UUID 直接 append 两次,load_transcript 仍只看到一次(行为对外不变)。

    实现层从写侧 dedup 改读侧 dedup,但外部契约保留 §7.4.3 幂等。
    保留先到的那条(load 时 seen set 先见 first)。
    """
    store = InMemoryStore()
    ss = SessionStore(store)
    e_first = SessionEntry(
        uuid="dup", type="user", content="first",
        user_id="u1", session_id="s1",
    )
    e_dup = SessionEntry(
        uuid="dup", type="user", content="dup-should-be-ignored",
        user_id="u1", session_id="s1",
    )
    await ss.append_entry(e_first)
    await ss.append_entry(e_dup)
    seq = await ss.load_transcript(user_id="u1", session_id="s1")
    assert len(seq) == 1
    assert seq[0].content == "first"


@pytest.mark.asyncio
async def test_inmemory_blob_append_basic():
    """Store.blob_append:InMemoryStore 两次 append 的 bytes 拼接。"""
    store = InMemoryStore()
    ns = Namespace(user_id="u1", scope="transcript")
    await store.blob_append(ns, "k", b"hello\n")
    await store.blob_append(ns, "k", b"world\n")
    assert await store.blob_get(ns, "k") == b"hello\nworld\n"


@pytest.mark.asyncio
async def test_inmemory_blob_append_creates_when_missing():
    """blob_append 在 key 不存在时直接创建(语义同 put + append)。"""
    store = InMemoryStore()
    ns = Namespace(user_id="u1", scope="transcript")
    await store.blob_append(ns, "new", b"chunk1")
    assert await store.blob_get(ns, "new") == b"chunk1"


@pytest.mark.asyncio
async def test_redis_blob_append_raises_not_implemented():
    """RedisStore.blob_append 与 blob_put 一致抛 NotImplementedError(Blob 走 PG)。"""
    pytest.importorskip("fakeredis")
    import fakeredis.aioredis

    from praxis2.store.redis import RedisStore

    client = fakeredis.aioredis.FakeRedis()
    st = RedisStore(client)
    ns = Namespace(user_id="u1", scope="transcript")
    with pytest.raises(NotImplementedError):
        await st.blob_append(ns, "k", b"x")
    await client.aclose()
