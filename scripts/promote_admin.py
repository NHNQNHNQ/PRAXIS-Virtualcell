"""把已注册用户升 admin(M12 完整管理面板前的运维口子)。

用法(staging .53 上):
    python -m scripts.promote_admin --email 2370309934@qq.com
    python -m scripts.promote_admin --email foo@bar --role user   # 降级也可

环境变量(若 --db-url 未传):
    PRAXIS_DB_URL                postgresql://praxis2:...@127.0.0.1:5432/praxis2
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from praxis2.auth.repository_pg import PgAuthRepository
from praxis2.store.pg import make_pg_pool


async def main_async(email: str, role: str, db_url: str) -> int:
    pool = await make_pg_pool(db_url)
    try:
        repo = PgAuthRepository(pool)
        user = await repo.get_user_by_email(email)
        if not user:
            print(f"[promote] 未找到 email={email!r} 用户;先在 UI 注册一次", file=sys.stderr)
            return 2
        if user.role == role:
            print(f"[promote] {email} 已经是 role={role},无需改动")
            return 0
        await repo.update_user_role(user.id, role=role)
        await repo.insert_audit(
            user_id=user.id,
            actor="system",
            action="role_change",
            resource="user",
            resource_id=str(user.id),
            ip=None,
            ua=None,
            meta={"from": user.role, "to": role},
        )
        print(f"[promote] OK: {email}  {user.role} → {role}  (user_id={user.id})")
        return 0
    finally:
        await pool.close()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--email", required=True, help="目标用户邮箱(必须已注册)")
    p.add_argument("--role", default="admin", choices=["user", "admin"], help="目标角色,默认 admin")
    p.add_argument("--db-url", default=os.environ.get("PRAXIS_DB_URL", ""),
                   help="PG URL;默认读 PRAXIS_DB_URL")
    args = p.parse_args()
    if not args.db_url:
        print("[promote] 缺 --db-url 或 PRAXIS_DB_URL 环境变量", file=sys.stderr)
        return 2
    return asyncio.run(main_async(args.email, args.role, args.db_url))


if __name__ == "__main__":
    raise SystemExit(main())
