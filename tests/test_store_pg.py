from __future__ import annotations

import pytest


def test_pg_store_imports_ok():
    from praxis2.store.pg import PgStore, make_pg_pool  # noqa: F401

    assert PgStore.__name__ == "PgStore"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pg_store_kv_set_get_delete():
    pytest.importorskip("testcontainers.postgres")

    from testcontainers.postgres import PostgresContainer

    from praxis2.store.base import Namespace
    from praxis2.store.pg import PgStore, make_pg_pool

    with PostgresContainer("postgres:16") as pg:
        url = pg.get_connection_url().replace("postgresql+psycopg2", "postgresql")
        pool = await make_pg_pool(url)
        st = PgStore(pool)
        ns = Namespace(user_id="u1", scope="session")
        await st.kv_set(ns, "k1", b"hello")
        assert await st.kv_get(ns, "k1") == b"hello"
        await st.kv_delete(ns, "k1")
        assert await st.kv_get(ns, "k1") is None
        await pool.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pg_store_meta_upsert_list():
    pytest.importorskip("testcontainers.postgres")

    from testcontainers.postgres import PostgresContainer

    from praxis2.store.pg import PgStore, make_pg_pool

    with PostgresContainer("postgres:16") as pg:
        url = pg.get_connection_url().replace("postgresql+psycopg2", "postgresql")
        pool = await make_pg_pool(url)
        st = PgStore(pool)
        await st.meta_upsert("sessions", {"user_id": "u1", "id": "s1", "title": "t1"})
        await st.meta_upsert("sessions", {"user_id": "u1", "id": "s2", "title": "t2"})
        rows = await st.meta_list("sessions", "u1")
        assert len(rows) == 2
        await pool.close()
