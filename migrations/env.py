"""Alembic env(M9):用 PRAXIS_DB_URL 环境变量,不读 alembic.ini sqlalchemy.url。

M9 不维护 SQLAlchemy ORM(用 asyncpg 直查);migration 用 raw SQL 经 op.execute。
"""

from __future__ import annotations

import os
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool


def _clean_apple_double() -> None:
    """T7/exFAT 等外挂盘 macOS 自动生成 ._* 元数据文件含 null bytes,
    alembic 扫 versions/ 时会试图 import 它们 → SyntaxError。
    启动期清掉本机 versions/ 下所有 ._* 防止干扰(idempotent)。"""
    vdir = Path(__file__).parent / "versions"
    if vdir.exists():
        for f in vdir.glob("._*"):
            try:
                f.unlink()
            except OSError:
                pass


_clean_apple_double()

config = context.config


def _get_url() -> str:
    url = os.environ.get("PRAXIS_DB_URL", "")
    if not url:
        raise RuntimeError("PRAXIS_DB_URL 未设置,无法运行 alembic")
    # alembic 跑 sync sqlalchemy,但 PRAXIS-2 用 asyncpg;URL 转回标准 postgresql://
    return url.replace("postgresql+asyncpg://", "postgresql://")


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section) or {}
    cfg["sqlalchemy.url"] = _get_url()
    connectable = engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
