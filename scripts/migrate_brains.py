"""Migrate selected local brain trees into PostgreSQL or an in-memory dry run."""

import argparse
import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path

from praxis2.brains.migrate import DISCIPLINE_SLUGS as _LEGACY_SLUGS
from praxis2.brains.migrate import migrate_dir_tree
from praxis2.brains.store import put_brain_doc
from praxis2.store.base import Store


@dataclass
class MigrationReport:
    attempted_slugs: list[str] = field(default_factory=list)
    migrated_slugs: list[str] = field(default_factory=list)
    skipped_empty: list[str] = field(default_factory=list)
    total_docs: int = 0
    errors: list[str] = field(default_factory=list)


async def migrate_all(
    root: Path,
    store: Store,
    *,
    user_id: str,
    slugs: "list[str] | None" = None,
) -> MigrationReport:
    """Migrate selected brain directories into the provided store and report per-brain results."""
    root = Path(root)
    targets = slugs if slugs is not None else _LEGACY_SLUGS
    report = MigrationReport(attempted_slugs=list(targets))
    for slug in targets:
        slug_root = root / slug
        if not slug_root.is_dir():
            report.errors.append(f"{slug}: Directory not found: {slug_root}")
            continue
        try:
            docs = migrate_dir_tree(slug_root, slug)
        except Exception as e:  # noqa: BLE001
            report.errors.append(f"{slug}: migrate_dir_tree failed: {e!r}")
            continue
        if not docs:
            report.skipped_empty.append(slug)
            continue
        for doc in docs:
            await put_brain_doc(store, user_id, doc)
        report.migrated_slugs.append(slug)
        report.total_docs += len(docs)
    return report


def _main() -> None:

    parser = argparse.ArgumentParser(prog="migrate_brains")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--user-id", required=True)
    parser.add_argument(
        "--slugs",
        nargs="*",
        default=None,
        help="Optional brain identifiers; defaults to the configured VirtualCell brain",
    )
    parser.add_argument(
        "--target",
        choices=["pg", "memory"],
        default="pg",
        help="pg persists to PostgreSQL; memory returns an in-memory dry-run report",
    )
    args = parser.parse_args()

    async def _run() -> MigrationReport:
        if args.target == "pg":
            from praxis2.store.pg import PgStore, make_pg_pool

            db_url = os.environ.get("PRAXIS_DB_URL", "").strip()
            if not db_url:
                raise ValueError("PRAXIS_DB_URL is required for --target=pg")
            pool = await make_pg_pool(db_url)
            try:
                store = PgStore(pool)
                return await migrate_all(
                    args.root,
                    store,
                    user_id=args.user_id,
                    slugs=args.slugs,
                )
            finally:
                await pool.close()
        else:
            from praxis2.store.memory import InMemoryStore

            store = InMemoryStore()
            return await migrate_all(
                args.root,
                store,
                user_id=args.user_id,
                slugs=args.slugs,
            )

    report = asyncio.run(_run())
    print(f"[migrate_brains] target={args.target}")
    print(f"[migrate_brains] attempted={report.attempted_slugs}")
    print(f"[migrate_brains] migrated={report.migrated_slugs}")
    print(f"[migrate_brains] skipped_empty={report.skipped_empty}")
    print(f"[migrate_brains] total_docs={report.total_docs}")
    print(f"[migrate_brains] PERSISTED to {args.target.upper()} ({len(report.migrated_slugs)} slugs)")
    if report.errors:
        print(f"[migrate_brains] errors={report.errors}")


if __name__ == "__main__":
    _main()
