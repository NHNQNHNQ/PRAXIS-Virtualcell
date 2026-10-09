import os
import subprocess
import sys

import pytest

from praxis2.brains.store import list_brain_docs
from praxis2.store.memory import InMemoryStore
from scripts.migrate_brains import (
    _LEGACY_SLUGS,
    MigrationReport,
    migrate_all,
)


def test_legacy_slugs_constant_lists_virtualcell():

    assert len(_LEGACY_SLUGS) == 1
    assert _LEGACY_SLUGS == ["virtualcell"]


async def test_migrate_all_smoke_with_synthetic_root(tmp_path):

    for slug in ("cryo", "dock"):
        rules_dir = tmp_path / slug / "memory" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "r1.md").write_text(f"# rule for {slug}")
        cases_dir = tmp_path / slug / "memory" / "cases"
        cases_dir.mkdir(parents=True)
        (cases_dir / "c1.md").write_text(f"# case for {slug}")
    store = InMemoryStore()
    report = await migrate_all(
        tmp_path,
        store,
        user_id="u_admin",
        slugs=["cryo", "dock"],
    )
    assert isinstance(report, MigrationReport)
    assert report.migrated_slugs == ["cryo", "dock"]
    assert report.total_docs >= 4

    cryo_docs = await list_brain_docs(store, "u_admin", "cryo")
    assert any(d.kind == "rules" for d in cryo_docs)
    assert any(d.kind == "cases" for d in cryo_docs)


async def test_migrate_all_common_dir_tolerated_no_error(tmp_path):

    common = tmp_path / "_common"
    (common / "memory" / "facts").mkdir(parents=True)
    (common / "skills" / "nature-citation").mkdir(parents=True)
    store = InMemoryStore()

    report = await migrate_all(
        tmp_path,
        store,
        user_id="u_admin",
        slugs=["_common"],
    )

    assert "_common" in report.attempted_slugs
    assert report.skipped_empty == ["_common"]


def test_cli_help_lists_target_option():

    result = subprocess.run(
        [sys.executable, "-m", "scripts.migrate_brains", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--target" in result.stdout
    assert "pg" in result.stdout
    assert "memory" in result.stdout


def test_cli_memory_target_dry_run(tmp_path):

    rules_dir = tmp_path / "cryo" / "memory" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "r1.md").write_text("# rule for cryo")

    env = {"PATH": os.environ.get("PATH", "")}

    env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.migrate_brains",
            "--root",
            str(tmp_path),
            "--user-id",
            "u_test",
            "--target",
            "memory",
            "--slugs",
            "cryo",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert "PERSISTED to MEMORY" in result.stdout
    assert "target=memory" in result.stdout
    assert "migrated=['cryo']" in result.stdout


@pytest.mark.integration
async def test_migrate_all_real_v1_brains_completeness():

    from pathlib import Path

    configured_root = os.environ.get("PRAXIS_TEST_BRAINS_ROOT", "")
    if not configured_root:
        pytest.skip("Set PRAXIS_TEST_BRAINS_ROOT to enable the local brain migration fixture")
    root = Path(configured_root)
    if not root.is_dir():
        pytest.skip(
            "v1 brains_snapshot \u4e0d\u5b58\u5728,\u8df3\u8fc7\u771f\u8fc1\u79fb\u5b8c\u6574\u6027\u65ad\u8a00"
        )
    store = InMemoryStore()
    report = await migrate_all(root, store, user_id="u_admin")

    assert set(report.migrated_slugs) >= set(_LEGACY_SLUGS)

    assert report.total_docs >= 20
