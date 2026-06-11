"""v1 用户表 dump → PRAXIS-2 schema 迁移(stub,真跑 v2.0 切换前)。

design §10.2 / §0.1 不干扰 v1 — M9 期间不连真 v1 db,仅用合成 dump 数据
验证迁移逻辑正确性。v2.0 切换 prep 时由用户提供真 v1 pg_dump JSON 跑此脚本。

合成 dump 格式:
[
  {"id": "uuid", "email": "...", "phone": null, "password_hash": "$argon2id$...",
   "display_name": "...", "role": "user|admin", "created_at": "ISO8601"},
  ...
]
"""

from __future__ import annotations

import sys
from collections.abc import Iterable

from praxis2.auth.errors import EmailConflict
from praxis2.auth.repository import AuthRepository


async def migrate_users_from_v1_dump(dump: Iterable[dict], *, repo: AuthRepository) -> int:
    """INSERT v1 users 到 PRAXIS-2 schema;duplicate email skip,返回迁移成功数。"""
    n = 0
    for row in dump:
        pw_hash = row["password_hash"]
        if isinstance(pw_hash, str):
            pw_hash = pw_hash.encode("utf-8")
        try:
            await repo.create_user(
                email=row["email"],
                password_hash=pw_hash,
                display_name=row.get("display_name"),
                role=row.get("role", "user"),
            )
            n += 1
        except EmailConflict:
            continue
    return n


def main():
    """CLI:python -m scripts.migrate_v1_users < dump.json(真跑前用户提供)。

    M9 默认拒绝执行(stub):需 --confirm-real-migration 显式确认才连真 db。
    """
    if "--confirm-real-migration" not in sys.argv:
        print("M9 stub:本脚本默认不连真 v1 db(§0.1 不干扰 v1)。", file=sys.stderr)
        print(
            "真跑 v2.0 切换前由用户提供 v1 pg_dump JSON + --confirm-real-migration 标志。",
            file=sys.stderr,
        )
        sys.exit(2)
    # 真跑分支(v2.0 阶段执行,M9 仅 stub):
    # dump = json.load(sys.stdin)
    # ... 真连 PG + 真 repo + 调 migrate_users_from_v1_dump


if __name__ == "__main__":
    main()
