"""§5⑦/§5⑨ migrate_brains 真灌入 + 领域知识完整性断言。"""

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


def test_legacy_slugs_constant_lists_13():
    # v2.0.2:Synth 真盘已落地(brains/synth/ + _brains/synth/)→ 13 学科
    assert len(_LEGACY_SLUGS) == 13
    assert _LEGACY_SLUGS == [
        "cell", "crispr", "cryo", "dock", "drug", "enzyme",
        "immuno", "md", "microbiome", "omics", "pharma", "protein", "synth",
    ]


async def test_migrate_all_smoke_with_synthetic_root(tmp_path):
    # 合成最小 v1 结构,断言 migrate_all 调 migrate_dir_tree + put_brain_doc 链路通
    # 不依赖真 /Volumes/T7/PRAXIS-Brains/_brains/(避免单元测试外部副作用)
    for slug in ("cryo", "dock"):
        rules_dir = tmp_path / slug / "memory" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "r1.md").write_text(f"# rule for {slug}")
        cases_dir = tmp_path / slug / "memory" / "cases"
        cases_dir.mkdir(parents=True)
        (cases_dir / "c1.md").write_text(f"# case for {slug}")
    store = InMemoryStore()
    report = await migrate_all(
        tmp_path, store, user_id="u_admin",
        slugs=["cryo", "dock"],
    )
    assert isinstance(report, MigrationReport)
    assert report.migrated_slugs == ["cryo", "dock"]
    assert report.total_docs >= 4  # 每 slug ≥ 2 doc(1 rule + 1 case)
    # 真断言入 store
    cryo_docs = await list_brain_docs(store, "u_admin", "cryo")
    assert any(d.kind == "rules" for d in cryo_docs)
    assert any(d.kind == "cases" for d in cryo_docs)


async def test_migrate_all_common_dir_tolerated_no_error(tmp_path):
    # _common 含 M5 不识别的 kind/dir(memory/facts/ skills/nature-*):
    # M5 返空 list → migrate_all 记 INFO 不报错(M8 容错路径)
    common = tmp_path / "_common"
    (common / "memory" / "facts").mkdir(parents=True)  # M5 不识别
    (common / "skills" / "nature-citation").mkdir(parents=True)  # 非 workflows
    store = InMemoryStore()
    # 不抛
    report = await migrate_all(
        tmp_path, store, user_id="u_admin", slugs=["_common"],
    )
    # 没识别到任何 doc,但 _common 仍在 migrated_slugs(记账)
    assert "_common" in report.attempted_slugs
    assert report.skipped_empty == ["_common"]


def test_cli_help_lists_target_option():
    """D.4(reviewer M0/M8 #7):`--help` 输出含 `--target choices`(pg|memory)。"""
    result = subprocess.run(
        [sys.executable, "-m", "scripts.migrate_brains", "--help"],
        capture_output=True, text=True, check=True,
    )
    assert "--target" in result.stdout
    assert "pg" in result.stdout
    assert "memory" in result.stdout


def test_cli_memory_target_dry_run(tmp_path):
    """D.4:`--target=memory` 不依赖 PRAXIS_* env(纯 dry-run InMemoryStore),
    输出含 `PERSISTED to MEMORY` 明示落点。"""
    # 合成最小 v1 结构(对应 _LEGACY_SLUGS 中的 cryo)
    rules_dir = tmp_path / "cryo" / "memory" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "r1.md").write_text("# rule for cryo")
    # 关键:env 仅传 PATH,不含 PRAXIS_* — 验证 memory target 真不读 load_from_env
    env = {"PATH": os.environ.get("PATH", "")}
    # PYTHONPATH 让 subprocess 能 import 仓内模块
    env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [
            sys.executable, "-m", "scripts.migrate_brains",
            "--root", str(tmp_path),
            "--user-id", "u_test",
            "--target", "memory",
            "--slugs", "cryo",
        ],
        capture_output=True, text=True, env=env, check=True,
    )
    assert "PERSISTED to MEMORY" in result.stdout
    assert "target=memory" in result.stdout
    assert "migrated=['cryo']" in result.stdout


@pytest.mark.integration
async def test_migrate_all_real_v1_brains_completeness():
    # §5⑦ 领域知识完整性断言(真跑 v1 brains_snapshot)
    # 标 integration:无 /Volumes/T7/PRAXIS-Brains 自动 skip(测试机适配)
    from pathlib import Path

    root = Path("/Volumes/T7/PRAXIS-Brains/_brains")
    if not root.is_dir():
        pytest.skip("v1 brains_snapshot 不存在,跳过真迁移完整性断言")
    store = InMemoryStore()
    report = await migrate_all(root, store, user_id="u_admin")
    # 12 学科全部迁移(§5⑦ 完整性)
    assert set(report.migrated_slugs) >= set(_LEGACY_SLUGS)
    # 至少 N 个文档落入 store(具体阈值留 §11.9 SLO 风格不强约,但 >=20)
    assert report.total_docs >= 20
