"""§5⑦/§5⑨ v1 brains_snapshot → store 真迁移脚本(M5 carry 落地)。

复用 M5 `brains.migrate.migrate_dir_tree` + `brains.store.put_brain_doc`,
M8 一次性运维灌入。**12 学科** `_LEGACY_SLUGS` 精确常量(M8 校准①:v1 真实
计数 12,非总纲 §6② 文字「13」)。

容错:`_common`/`_meta` 等 M5 函数不识别的 kind/dir → 返空 list 时记 INFO
不报错(M5 已用 `_SLUG_CASE_HINTS` 与 M3 builtin hook 硬编码核心规则,
v1 富 `_common` 内容沉淀属 v2 brains 扩展)。

CLI 用法:
    python -m scripts.migrate_brains \\
        --root /Volumes/T7/PRAXIS-Brains/_brains \\
        --user-id u_admin
"""

import argparse
import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from praxis2.brains.migrate import DISCIPLINE_SLUGS as _LEGACY_SLUGS
from praxis2.brains.migrate import migrate_dir_tree
from praxis2.brains.store import put_brain_doc
from praxis2.store.base import Store

# B.3:_LEGACY_SLUGS 复用 brains.migrate.DISCIPLINE_SLUGS 单源(12 lowercase),
# 防 4 处源头漂移(reviewer M5 C1+C2);不变式 test_correctness_slug_canonical 锁。


@dataclass
class MigrationReport:
    attempted_slugs: list[str] = field(default_factory=list)
    migrated_slugs: list[str] = field(default_factory=list)
    skipped_empty: list[str] = field(default_factory=list)  # M5 函数返空 list 的 slug
    total_docs: int = 0
    errors: list[str] = field(default_factory=list)


async def migrate_all(
    root: Path,
    store: Store,
    *,
    user_id: str,
    slugs: "list[str] | None" = None,
) -> MigrationReport:
    """对 root 下每个 slug 跑 `migrate_dir_tree → put_brain_doc`。
    `slugs` 默认 `_LEGACY_SLUGS`(12 学科);可传 `["_common"]` 单测容错。
    每 slug 失败不互拖(记 errors),空 doc 列表记 skipped_empty。"""
    root = Path(root)
    targets = slugs if slugs is not None else _LEGACY_SLUGS
    report = MigrationReport(attempted_slugs=list(targets))
    for slug in targets:
        slug_root = root / slug
        if not slug_root.is_dir():
            report.errors.append(f"{slug}: 目录不存在 {slug_root}")
            continue
        try:
            docs = migrate_dir_tree(slug_root, slug)
        except Exception as e:  # noqa: BLE001 - 容错隔离,errors 记账不互拖
            report.errors.append(f"{slug}: migrate_dir_tree 异常 {e!r}")
            continue
        if not docs:
            # M5 函数不识别 kind/dir(如 _common 的 memory/facts、skills/nature-*)
            # → 返空 list;M8 记 INFO 不报错(M5 carry 容错)
            report.skipped_empty.append(slug)
            continue
        for doc in docs:
            await put_brain_doc(store, user_id, doc)
        report.migrated_slugs.append(slug)
        report.total_docs += len(docs)
    return report


def _main() -> None:
    """CLI 入口:`python -m scripts.migrate_brains --root <path> --user-id <id>`。

    D.4(reviewer M0/M8 #7):`--target=pg`(默认)真持久化到 PG;
    `--target=memory` 走 InMemoryStore dry-run(不读 load_from_env,无须 PRAXIS_DB_URL)。
    旧版默认 InMemoryStore 跑完丢弃,README 步骤误导用户以为"灌入"成功 — 本次校准。"""
    parser = argparse.ArgumentParser(prog="migrate_brains")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--user-id", required=True)
    parser.add_argument(
        "--slugs", nargs="*", default=None,
        help="可选:仅迁移指定 slug(默认 12 学科全跑)",
    )
    parser.add_argument(
        "--target", choices=["pg", "memory"], default="pg",
        help="pg=持久化到 PG(默认);memory=dry-run InMemoryStore(只看 report)",
    )
    args = parser.parse_args()

    async def _run() -> MigrationReport:
        if args.target == "pg":
            from praxis2.config import load_from_env
            from praxis2.store.pg import PgStore, make_pg_pool

            settings = load_from_env()
            pool = await make_pg_pool(settings.db_url)
            try:
                store = PgStore(pool)
                return await migrate_all(
                    args.root, store, user_id=args.user_id, slugs=args.slugs,
                )
            finally:
                # asyncpg Pool 真 API:`await pool.close()`(等待 in-flight 连接释放)
                await pool.close()
        else:
            from praxis2.store.memory import InMemoryStore

            store = InMemoryStore()
            return await migrate_all(
                args.root, store, user_id=args.user_id, slugs=args.slugs,
            )

    report = asyncio.run(_run())
    print(f"[migrate_brains] target={args.target}")
    print(f"[migrate_brains] attempted={report.attempted_slugs}")
    print(f"[migrate_brains] migrated={report.migrated_slugs}")
    print(f"[migrate_brains] skipped_empty={report.skipped_empty}")
    print(f"[migrate_brains] total_docs={report.total_docs}")
    print(
        f"[migrate_brains] PERSISTED to {args.target.upper()} "
        f"({len(report.migrated_slugs)} slugs)"
    )
    if report.errors:
        print(f"[migrate_brains] errors={report.errors}")


if __name__ == "__main__":
    _main()
