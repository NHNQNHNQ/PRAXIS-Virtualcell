"""migrations/versions/001_initial_auth.py 单元 + integration。

单元层校验:migration 模块可 import、含 upgrade/downgrade、revision id 形式合规。
integration(@pytest.mark.integration)层:真起 testcontainers postgres,跑 upgrade,
查表存在 + pgcrypto extension + partial unique index 行为。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_MIG_PATH = Path("migrations/versions/001_initial_auth.py")


def _load_migration():
    spec = importlib.util.spec_from_file_location("mig001", _MIG_PATH)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mig001"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_migration_file_exists():
    assert _MIG_PATH.exists(), "001 initial migration file missing"


def test_migration_has_upgrade_and_downgrade():
    m = _load_migration()
    assert callable(m.upgrade)
    assert callable(m.downgrade)


def test_migration_revision_metadata():
    m = _load_migration()
    assert m.revision == "001_initial_auth"
    assert m.down_revision is None


def test_alembic_ini_exists():
    assert Path("alembic.ini").exists(), "alembic.ini missing"


def test_env_py_exists():
    assert Path("migrations/env.py").exists(), "migrations/env.py missing"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upgrade_creates_three_tables():
    """testcontainers 起 postgres,跑 upgrade,断言 3 表 + pgcrypto + partial unique。"""
    pytest.importorskip("testcontainers.postgres")
    pytest.importorskip("asyncpg")
    import os
    import subprocess
    import sys

    import asyncpg
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16") as pg:
        url = pg.get_connection_url().replace("postgresql+psycopg2", "postgresql")
        env = {**os.environ, "PRAXIS_DB_URL": url}
        proc = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0, f"alembic upgrade failed: {proc.stderr}"

        conn = await asyncpg.connect(url)
        try:
            tables = await conn.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
            )
            names = {r["tablename"] for r in tables}
            assert {"users", "email_codes", "audit_log"} <= names

            exts = await conn.fetch("SELECT extname FROM pg_extension")
            assert "pgcrypto" in {r["extname"] for r in exts}

            idx = await conn.fetch(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE tablename='users' AND indexname='uq_users_email'"
            )
            assert idx, "uq_users_email index missing"
            assert "WHERE" in idx[0]["indexdef"]
            assert "deleted_at" in idx[0]["indexdef"]
        finally:
            await conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upgrade_idempotent_on_already_upgraded_db():
    pytest.importorskip("testcontainers.postgres")
    import os
    import subprocess
    import sys

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16") as pg:
        url = pg.get_connection_url().replace("postgresql+psycopg2", "postgresql")
        env = {**os.environ, "PRAXIS_DB_URL": url}
        p1 = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert p1.returncode == 0
        # 第二次 upgrade(空 op,alembic version 表自管)
        p2 = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert p2.returncode == 0, f"second upgrade failed: {p2.stderr}"
