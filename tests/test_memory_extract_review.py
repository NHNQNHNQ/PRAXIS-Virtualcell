from praxis2.brains.store import list_brain_docs
from praxis2.memory.extract import ExtractCandidate, extract_candidates, persist_candidates
from praxis2.memory.review import approve, list_pending, reject
from praxis2.store.base import Namespace
from praxis2.store.memory import InMemoryStore


def test_extract_from_failure_point_produces_candidate():
    transcript = [
        {"role": "user", "content": "做 X"},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1",
                                      "is_error": True, "content": "失败:超时"}]},
    ]
    cands = extract_candidates(transcript, trigger="tool_failure")
    assert len(cands) >= 1
    assert cands[0].trigger == "tool_failure"
    assert "超时" in cands[0].text


async def test_persist_is_idempotent_and_pending_visible():
    store = InMemoryStore()
    ns = Namespace(user_id="u1", scope="session")
    c = ExtractCandidate(id="c1", text="经验:超时重试", trigger="tool_failure")
    await persist_candidates(store, ns, [c])
    await persist_candidates(store, ns, [c])  # 重复 persist 幂等
    pend = await list_pending(store, ns)
    assert len(pend) == 1 and pend[0]["id"] == "c1"


async def test_approve_promotes_and_reject_records_reason():
    store = InMemoryStore()
    ns = Namespace(user_id="u1", scope="session")
    await persist_candidates(store, ns, [
        ExtractCandidate(id="c1", text="t1", trigger="manual"),
        ExtractCandidate(id="c2", text="t2", trigger="manual"),
    ])
    await approve(store, ns, "c1", brain_slug="general")
    await reject(store, ns, "c2", reason="不具普适性")
    pend = await list_pending(store, ns)
    assert pend == []  # 两条都出队
    # promote 写入真实大脑落点 brains/general(M5 经 put_brain_doc 落 cases/c1 键)
    # M4 前置接口升级为 M5 真实落点:改用 list_brain_docs 同口径校验
    promoted = await list_brain_docs(store, "u1", "general")
    assert any(d.stem == "c1" or "t1" in d.text for d in promoted)
    # reject 记因审计
    rej = await store.kv_get(ns, "_reject/c2")
    assert rej is not None and "不具普适性".encode() in rej


async def test_pending_candidates_isolated_across_ns():
    # §7.4.2 关键不变量:未审候选只对本 (user,scope) 可见,不跨 ns 泄漏
    store = InMemoryStore()
    ns_a = Namespace(user_id="u1", scope="session")
    ns_b = Namespace(user_id="u1", scope="session2")
    ns_other = Namespace(user_id="u2", scope="session")
    await persist_candidates(
        store, ns_a, [ExtractCandidate(id="a1", text="ta", trigger="manual")]
    )
    assert [p["id"] for p in await list_pending(store, ns_a)] == ["a1"]
    assert await list_pending(store, ns_b) == []      # 同 user 跨 scope 不可见
    assert await list_pending(store, ns_other) == []  # 跨 user 不可见
