from praxis2.brains.store import list_brain_docs
from praxis2.memory.extract import ExtractCandidate, persist_candidates
from praxis2.memory.review import (
    BrainCacheRegistry,
    approve,
    list_pending,
    reject,
)
from praxis2.store.base import Namespace
from praxis2.store.memory import InMemoryStore


def _ns():
    return Namespace(user_id="u1", scope="session")


async def test_approve_promotes_candidate_into_real_brain_slug():
    store = InMemoryStore()
    ns = _ns()
    await persist_candidates(store, ns, [
        ExtractCandidate(id="cand-1", text="新经验:某流程要点", trigger="manual"),
    ])
    assert len(await list_pending(store, ns)) == 1
    await approve(store, ns, "cand-1", brain_slug="Cryo")
    docs = await list_brain_docs(store, "u1", "Cryo")
    assert any("某流程要点" in d.text for d in docs)
    assert len(await list_pending(store, ns)) == 0


async def test_approve_to_general_when_cross_discipline():
    store = InMemoryStore()
    ns = _ns()
    await persist_candidates(store, ns, [
        ExtractCandidate(id="c2", text="跨学科经验", trigger="manual"),
    ])
    await approve(store, ns, "c2", brain_slug="general")
    docs = await list_brain_docs(store, "u1", "general")
    assert any("跨学科经验" in d.text for d in docs)


async def test_approve_triggers_hot_reload_cache_invalidation():
    store = InMemoryStore()
    ns = _ns()
    reg = BrainCacheRegistry()
    reg.mark_loaded("Cryo")
    assert reg.is_loaded("Cryo") is True
    await persist_candidates(store, ns, [
        ExtractCandidate(id="c3", text="新案例", trigger="manual"),
    ])
    await approve(store, ns, "c3", brain_slug="Cryo", cache=reg)
    assert reg.is_loaded("Cryo") is False


async def test_unreviewed_candidate_not_in_brain_until_approved():
    store = InMemoryStore()
    ns = _ns()
    await persist_candidates(store, ns, [
        ExtractCandidate(id="c4", text="未审内容", trigger="manual"),
    ])
    assert await list_brain_docs(store, "u1", "Cryo") == []


async def test_reject_records_reason_and_not_promoted():
    store = InMemoryStore()
    ns = _ns()
    await persist_candidates(store, ns, [
        ExtractCandidate(id="c5", text="错误经验", trigger="manual"),
    ])
    await reject(store, ns, "c5", reason="无 DOI 不可溯源")
    assert await list_brain_docs(store, "u1", "Cryo") == []
    raw = await store.kv_get(ns, "_reject/c5")
    assert raw is not None and b"DOI" in raw


async def test_m4_signature_compat_approve_reject_list_pending():
    # M4 已有签名零回归:approve/reject/list_pending 三者均不变
    import inspect
    sa = inspect.signature(approve)
    assert "brain_slug" in sa.parameters
    assert sa.parameters["brain_slug"].kind == inspect.Parameter.KEYWORD_ONLY
    sr = inspect.signature(reject)
    assert list(sr.parameters) == ["store", "ns", "cand_id", "reason"]
    assert sr.parameters["reason"].kind == inspect.Parameter.KEYWORD_ONLY
    sl = inspect.signature(list_pending)
    assert list(sl.parameters) == ["store", "ns"]


async def test_approve_empty_slug_raises_before_dequeue_candidate_preserved():
    # Important 回归:空 slug fail-fast 须在出队前 → 候选不丢失
    store = InMemoryStore()
    ns = _ns()
    await persist_candidates(store, ns, [
        ExtractCandidate(id="c6", text="不该丢的候选", trigger="manual"),
    ])
    import pytest
    with pytest.raises(ValueError, match="不得为空"):
        await approve(store, ns, "c6", brain_slug="")
    # 候选仍在待审队列(未被静默吞掉)
    assert len(await list_pending(store, ns)) == 1
