import pytest

from praxis2.store.base import Namespace
from praxis2.store.memory import InMemoryStore


def test_namespace_requires_user_id():

    with pytest.raises(ValueError):
        Namespace(user_id="", scope="session")


async def test_kv_set_get_delete_and_ttl_marker():
    s = InMemoryStore()
    ns = Namespace(user_id="u1", scope="session")
    await s.kv_set(ns, "k", b"v")
    assert await s.kv_get(ns, "k") == b"v"
    await s.kv_delete(ns, "k")
    assert await s.kv_get(ns, "k") is None


async def test_tenant_isolation():
    s = InMemoryStore()
    a = Namespace(user_id="A", scope="memory")
    b = Namespace(user_id="B", scope="memory")
    await s.kv_set(a, "secret", b"a-only")
    assert await s.kv_get(b, "secret") is None


async def test_blob_put_get():
    s = InMemoryStore()
    ns = Namespace(user_id="u1", scope="transcript")
    ref = await s.blob_put(ns, "t1", b"big-bytes")
    assert isinstance(ref, str)
    assert await s.blob_get(ns, "t1") == b"big-bytes"


async def test_meta_upsert_get_list_scoped_by_user():
    s = InMemoryStore()
    await s.meta_upsert("sessions", {"user_id": "u1", "pk": "s1", "title": "A"})
    await s.meta_upsert("sessions", {"user_id": "u1", "pk": "s1", "title": "A2"})
    await s.meta_upsert("sessions", {"user_id": "u2", "pk": "s9", "title": "Z"})
    assert (await s.meta_get("sessions", "u1", "s1"))["title"] == "A2"
    rows = await s.meta_list("sessions", "u1")
    assert len(rows) == 1 and rows[0]["pk"] == "s1"


async def test_meta_upsert_requires_user_id_and_pk():
    s = InMemoryStore()
    with pytest.raises(ValueError):
        await s.meta_upsert("sessions", {"pk": "s1"})
    with pytest.raises(ValueError):
        await s.meta_upsert("sessions", {"user_id": "u1"})


async def test_meta_get_returns_copy_not_internal_ref():

    s = InMemoryStore()
    await s.meta_upsert("sessions", {"user_id": "u1", "pk": "s1", "title": "A"})
    got = await s.meta_get("sessions", "u1", "s1")
    got["title"] = "MUTATED"
    assert (await s.meta_get("sessions", "u1", "s1"))["title"] == "A"
