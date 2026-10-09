import pytest

from praxis2.brains.migrate import (
    DISCIPLINE_SLUGS,
    THREE_LAYER_DIRS,
    build_fixture_brain,
    migrate_dir_tree,
)
from praxis2.brains.store import (
    BrainDoc,
    brain_ns,
    list_brain_docs,
    put_brain_doc,
)
from praxis2.store.memory import InMemoryStore


def test_discipline_slugs_lowercase_single_virtualcell():
    # PRAXIS-virtualcell:13 通用学科脑已移除,改为单一 virtualcell 大脑。
    # (单源不变式由 tests/test_correctness_slug_canonical.py 锁 4 处)
    assert DISCIPLINE_SLUGS == ["virtualcell"]
    assert len(DISCIPLINE_SLUGS) == 1


def test_three_layer_structure_contract_matches_v1():
    # v1 §2.1 固定结构 + 四合并接口键
    assert set(THREE_LAYER_DIRS) == {
        "cases", "neg_cases", "rules", "skills",
    }


def test_brain_ns_enforces_user_id_and_scope_brain_slug():
    ns = brain_ns("u1", "Cryo")
    assert ns.user_id == "u1"
    assert ns.scope == "brain:Cryo"  # 对齐 M4 review.approve 前置接口
    with pytest.raises(ValueError):
        brain_ns("", "Cryo")  # §11.6 user_id 不能空


def test_fixture_brain_has_each_of_four_kinds():
    docs = build_fixture_brain("Cryo")
    kinds = {d.kind for d in docs}
    assert kinds == {"cases", "neg_cases", "rules", "skills"}
    assert all(isinstance(d, BrainDoc) for d in docs)
    assert all(d.slug == "Cryo" for d in docs)


def test_common_is_rules_only_not_domain_knowledge():
    # S11:_common 纯规则(RMCP/安全),非领域 case 知识
    docs = build_fixture_brain("_common")
    assert {d.kind for d in docs} == {"rules"}


def test_general_is_independent_brain_with_knowledge():
    # S11:general 与 13 学科并列的独立大脑(有可检索领域知识)
    docs = build_fixture_brain("general")
    assert "cases" in {d.kind for d in docs}


async def test_put_and_list_brain_docs_round_trip_via_store():
    store = InMemoryStore()
    docs = build_fixture_brain("Enzyme")
    for d in docs:
        await put_brain_doc(store, "u1", d)
    got = await list_brain_docs(store, "u1", "Enzyme")
    assert len(got) == len(docs)
    assert {g.stem for g in got} == {d.stem for d in docs}


async def test_user_isolation_across_brain_namespace():
    # §11.6:用户 A 写的大脑文档,用户 B 读不到
    store = InMemoryStore()
    await put_brain_doc(store, "A", build_fixture_brain("Cryo")[0])
    assert await list_brain_docs(store, "B", "Cryo") == []


async def test_reput_same_doc_is_idempotent_overwrite_not_duplicate():
    # 同 slug/kind/stem 重复 put(M5-T10 promote 重复审核场景)→ 覆盖非重复
    store = InMemoryStore()
    await put_brain_doc(store, "u1", BrainDoc("Cryo", "cases", "c1", "旧"))
    await put_brain_doc(store, "u1", BrainDoc("Cryo", "cases", "c1", "新"))
    got = await list_brain_docs(store, "u1", "Cryo")
    assert len(got) == 1                 # pk 覆盖,不产重复 index 行
    assert got[0].text == "新"


def test_migrate_dir_tree_pure_function_from_disk_layout(tmp_path):
    # 运维步骤:拿到 brains_snapshot 后从磁盘目录树灌入(非占位,真实纯函数)
    root = tmp_path / "Cryo"
    (root / "memory" / "cases").mkdir(parents=True)
    (root / "memory" / "cases" / "_neg").mkdir(parents=True)
    (root / "memory" / "rules").mkdir(parents=True)
    (root / "skills" / "workflows" / "wf1").mkdir(parents=True)
    (root / "skills" / "workflows" / "wf2_no_skillmd").mkdir(parents=True)
    (root / "memory" / "cases" / "c1.md").write_text("case 正文")
    (root / "memory" / "cases" / "_skip.md").write_text("下划线前缀跳过")
    (root / "memory" / "cases" / "_neg" / "NEG-1.md").write_text("反例")
    (root / "memory" / "rules" / "r1.md").write_text("规则")
    (root / "skills" / "workflows" / "wf1" / "SKILL.md").write_text(
        "---\nname: wf1\ndescription: d\n---\n"
    )
    docs = migrate_dir_tree(root, "Cryo")
    by = {(d.kind, d.stem) for d in docs}
    assert ("cases", "c1") in by
    assert ("neg_cases", "NEG-1") in by
    assert ("rules", "r1") in by
    assert ("skills", "wf1") in by
    # _ 前缀正例排除(v1 §2.1:Brain.cases() 自动跳过 _ 前缀)
    assert ("cases", "_skip") not in by
    # 无 SKILL.md 的 workflow 目录 → text 退化为目录名(有意 fallback)
    wf2 = next(d for d in docs if d.kind == "skills" and d.stem == "wf2_no_skillmd")
    assert wf2.text == "wf2_no_skillmd"
