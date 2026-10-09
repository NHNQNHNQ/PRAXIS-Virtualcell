"""创首个 admin 用户(M9 ship 后 staging .53 跑一次)。

用法:
    python -m scripts.create_admin --email admin@p --password 'pw' \\
        --display-name "Admin" --pepper "${PRAXIS_PASSWORD_PEPPER}"

或自动从环境取 db_url/pepper:
    python -m scripts.create_admin --email admin@p --password 'pw' --display-name "Admin"
"""

from __future__ import annotations

import argparse
import asyncio
import os

from praxis2.auth.repository import AuthRepository
from praxis2.auth.service import hash_password


async def create_admin(
    *,
    repo: AuthRepository,
    email: str,
    password: str,
    display_name: str,
    pepper: str,
) -> str:
    """创 admin user + 写 audit_log,返回 user_id。"""
    pw_hash = hash_password(password, pepper=pepper)
    user = await repo.create_user(
        email=email,
        password_hash=pw_hash,
        display_name=display_name,
        role="admin",
    )
    await repo.insert_audit(
        user_id=user.id,
        actor="system",
        action="admin_seed",
        resource="user",
        resource_id=user.id,
        ip=None,
        ua=None,
        meta={"by": "scripts/create_admin.py"},
    )
    return user.id


def _make_repo_from_env():
    """从环境变量构造默认 PgAuthRepository(CLI 入口默认工厂)。

    测试通过 monkeypatch 替换为 FakeAuthRepository,绕开 PG 依赖。
    返回 (repo, pool_or_none):pool 非 None 时调用方负责 close。
    """
    from praxis2.auth.repository_pg import PgAuthRepository
    from praxis2.store.pg import make_pg_pool

    url = os.environ.get("PRAXIS_DB_URL", "")
    if not url:
        raise SystemExit("PRAXIS_DB_URL 未设置")
    # 注意:这里返回 None pool — 真 _run 路径自己建 pool(同一 loop)。
    # 本函数仅作 test monkeypatch 缝(test 不真连 PG)。
    return PgAuthRepository, make_pg_pool


async def _run(args) -> str:
    """同一 loop 内建 pool + repo + create — 避免 Python 3.13 跨-loop Future 报错。

    M10.5 后补:为 test 提供 _make_repo_from_env monkeypatch 缝。test 可
    monkeypatch _make_repo_from_env 返一个工厂,让 CLI 走 Fake repo 不连 PG。
    """
    from praxis2.accounting.ledger import Ledger

    # M10.5 后补:test 可 monkeypatch _make_repo_from_env 注入 FakeAuthRepository
    # (callable / 直接对象);默认走真 PG 路径(下方原 PgAuthRepository + make_pg_pool)
    factory = _make_repo_from_env()
    # factory 形态二:(RepoCls, make_pg_pool) — 真生产路径,自建 pool
    # factory 形态一:repo 实例 — test 路径,跳过 pool / ledger 充值
    if isinstance(factory, tuple) and len(factory) == 2:
        repo_cls, make_pool = factory
        url = os.environ.get("PRAXIS_DB_URL", "")
        if not url:
            raise SystemExit("PRAXIS_DB_URL 未设置")
        pool = await make_pool(url)
        try:
            repo = repo_cls(pool)
            user_id = await create_admin(
                repo=repo,
                email=args.email,
                password=args.password,
                display_name=args.display_name,
                pepper=args.pepper,
            )
            if args.initial_balance_li > 0:
                ledger = Ledger(pool)
                async with pool.acquire() as conn:
                    async with conn.transaction():
                        await ledger.record(
                            conn, user_id, args.initial_balance_li,
                            kind="admin_seed_topup", ref_type="user", ref_id=user_id,
                            meta={"by": "create_admin.py"},
                        )
            return user_id
        finally:
            await pool.close()
    # test 路径:factory 是 repo 实例(monkeypatch 直接给 FakeAuthRepository)
    return await create_admin(
        repo=factory,
        email=args.email,
        password=args.password,
        display_name=args.display_name,
        pepper=args.pepper,
    )


def main():
    p = argparse.ArgumentParser(description="创首个 admin user(M9 ship 后跑一次)")
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--display-name", required=True)
    p.add_argument("--pepper", default=os.environ.get("PRAXIS_PASSWORD_PEPPER", ""))
    p.add_argument(
        "--initial-balance-li", type=int, default=0,
        help="可选:创建后立即充值 li (1 元 = 10 li,例 1000000 = 10 万元)",
    )
    args = p.parse_args()
    if not args.pepper:
        raise SystemExit("--pepper 或 PRAXIS_PASSWORD_PEPPER 必须给")

    user_id = asyncio.run(_run(args))
    print(f"已创建 admin user:{user_id} ({args.email})")


if __name__ == "__main__":
    main()
