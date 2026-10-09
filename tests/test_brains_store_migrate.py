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

    assert DISCIPLINE_SLUGS == ["virtualcell"]
    assert len(DISCIPLINE_SLUGS) == 1


def test_three_layer_structure_contract_matches_v1():

    assert set(THREE_LAYER_DIRS) == {
        "cases",
        "neg_cases",
        "rules",
        "skills",
    }


def test_brain_ns_enforces_user_id_and_scope_brain_slug():
    ns = brain_ns("u1", "Cryo")
    assert ns.user_id == "u1"
    assert ns.scope == "brain:Cryo"
    with pytest.raises(ValueError):
        brain_ns("", "Cryo")


def test_fixture_brain_has_each_of_four_kinds():
    docs = build_fixture_brain("Cryo")
    kinds = {d.kind for d in docs}
    assert kinds == {"cases", "neg_cases", "rules", "skills"}
    assert all(isinstance(d, BrainDoc) for d in docs)
    assert all(d.slug == "Cryo" for d in docs)


def test_common_is_rules_only_not_domain_knowledge():

    docs = build_fixture_brain("_common")
    assert {d.kind for d in docs} == {"rules"}


def test_general_is_independent_brain_with_knowledge():

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

    store = InMemoryStore()
    await put_brain_doc(store, "A", build_fixture_brain("Cryo")[0])
    assert await list_brain_docs(store, "B", "Cryo") == []


async def test_reput_same_doc_is_idempotent_overwrite_not_duplicate():

    store = InMemoryStore()
    await put_brain_doc(store, "u1", BrainDoc("Cryo", "cases", "c1", "\u65e7"))
    await put_brain_doc(store, "u1", BrainDoc("Cryo", "cases", "c1", "\u65b0"))
    got = await list_brain_docs(store, "u1", "Cryo")
    assert len(got) == 1
    assert got[0].text == "\u65b0"


def test_migrate_dir_tree_pure_function_from_disk_layout(tmp_path):

    root = tmp_path / "Cryo"
    (root / "memory" / "cases").mkdir(parents=True)
    (root / "memory" / "cases" / "_neg").mkdir(parents=True)
    (root / "memory" / "rules").mkdir(parents=True)
    (root / "skills" / "workflows" / "wf1").mkdir(parents=True)
    (root / "skills" / "workflows" / "wf2_no_skillmd").mkdir(parents=True)
    (root / "memory" / "cases" / "c1.md").write_text("case \u6b63\u6587")
    (root / "memory" / "cases" / "_skip.md").write_text("\u4e0b\u5212\u7ebf\u524d\u7f00\u8df3\u8fc7")
    (root / "memory" / "cases" / "_neg" / "NEG-1.md").write_text("\u53cd\u4f8b")
    (root / "memory" / "rules" / "r1.md").write_text("\u89c4\u5219")
    (root / "skills" / "workflows" / "wf1" / "SKILL.md").write_text("---\nname: wf1\ndescription: d\n---\n")
    docs = migrate_dir_tree(root, "Cryo")
    by = {(d.kind, d.stem) for d in docs}
    assert ("cases", "c1") in by
    assert ("neg_cases", "NEG-1") in by
    assert ("rules", "r1") in by
    assert ("skills", "wf1") in by

    assert ("cases", "_skip") not in by

    wf2 = next(d for d in docs if d.kind == "skills" and d.stem == "wf2_no_skillmd")
    assert wf2.text == "wf2_no_skillmd"
