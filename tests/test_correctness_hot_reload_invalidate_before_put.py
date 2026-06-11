"""D.7(reviewer M5 #3):approve 流程 bump version 早于 put_brain_doc,
防 stale cache 命中(竞态:put 完成前 retriever 见 is_loaded=True 复用旧 docs)。

BrainCacheRegistry 加 version 计数 + 显式 bump API;approve 改为
bump → put 顺序。窗口期内并发 retriever 见 version 增,主动重读 store,
即便此时 put 未完仍读到当前最新版(非完美原子,但比之前好:不会用
cached stale)。invalidate(slug) 旧 API 保持:discard loaded + bump version,
M4/M5 既有调用方零破坏。M5 内存版无 cache 选择路径,本 task 为 M6/M7
真后端 Redis 缓存接入预留接口位(总纲 §7.4.2)。"""

import pytest

from praxis2.memory.extract import ExtractCandidate, persist_candidates
from praxis2.memory.review import BrainCacheRegistry, approve
from praxis2.store.base import Namespace
from praxis2.store.memory import InMemoryStore


def _ns() -> Namespace:
    return Namespace(user_id="u1", scope="session")


def test_bump_increments_version_and_clears_loaded():
    """bump 兼容旧 invalidate 语义:同时 discard loaded 与 +1 version。"""
    cache = BrainCacheRegistry()
    cache.mark_loaded("cryo")
    assert cache.is_loaded("cryo") is True
    v0 = cache.version("cryo")
    new_v = cache.bump("cryo")
    assert new_v == v0 + 1
    assert cache.is_loaded("cryo") is False


def test_version_starts_at_zero_for_unknown_slug():
    """未见过的 slug version=0(不抛 KeyError,默认值语义)。"""
    cache = BrainCacheRegistry()
    assert cache.version("never_seen") == 0


def test_invalidate_legacy_api_still_bumps_version():
    """既有 cache.invalidate(slug) 调用方零破坏:它现在也 bump version。
    M4/M5 既有 server/routes/admin/review.py 等无须改动。"""
    cache = BrainCacheRegistry()
    v0 = cache.version("cryo")
    cache.invalidate("cryo")
    assert cache.version("cryo") == v0 + 1


def test_bump_multiple_times_monotonic():
    """连续 bump version 单调递增(并发 retriever 比版本号判 stale 的基础)。"""
    cache = BrainCacheRegistry()
    cache.bump("cryo")
    cache.bump("cryo")
    cache.bump("cryo")
    assert cache.version("cryo") == 3


async def test_approve_bumps_version_before_put_brain_doc(monkeypatch):
    """invariant:put_brain_doc 被调时 version 必须已 bump(invalidate-before-put)。
    并发 retriever 在 put 完成前已能看到 version 增,主动重读 store(不用 stale)。"""
    cache = BrainCacheRegistry()
    cache.mark_loaded("cryo")
    v_before = cache.version("cryo")

    store = InMemoryStore()
    ns = _ns()
    await persist_candidates(store, ns, [
        ExtractCandidate(id="cand-1", text="bump-before-put 测试", trigger="manual"),
    ])

    # 在 put_brain_doc 入口处快照 version,验证已 bump
    from praxis2.memory import review as review_mod
    orig_put = review_mod.put_brain_doc
    version_at_put: list[int] = []

    async def spy_put(store_, user_id, doc):
        version_at_put.append(cache.version("cryo"))
        await orig_put(store_, user_id, doc)

    monkeypatch.setattr(review_mod, "put_brain_doc", spy_put)

    await approve(store, ns, "cand-1", brain_slug="cryo", cache=cache)

    # put_brain_doc 被调用时,version 必须已经 +1(bump-before-put)
    assert version_at_put == [v_before + 1]
    # 且 loaded 标记也已清(旧语义保持)
    assert cache.is_loaded("cryo") is False


async def test_approve_without_cache_no_version_tracking_no_crash():
    """cache=None 路径(M4 兼容)approve 不应崩溃(回归保护)。"""
    store = InMemoryStore()
    ns = _ns()
    await persist_candidates(store, ns, [
        ExtractCandidate(id="cand-x", text="无 cache 路径", trigger="manual"),
    ])
    # 不传 cache,不应抛
    await approve(store, ns, "cand-x", brain_slug="cryo")


async def test_approve_empty_slug_does_not_bump_version():
    """fail-fast(空 slug)早于 _dequeue 与 bump,version 不应被错误递增。"""
    cache = BrainCacheRegistry()
    cache.mark_loaded("cryo")
    v_before = cache.version("cryo")
    store = InMemoryStore()
    ns = _ns()
    await persist_candidates(store, ns, [
        ExtractCandidate(id="cand-y", text="不该 bump 的", trigger="manual"),
    ])
    with pytest.raises(ValueError, match="不得为空"):
        await approve(store, ns, "cand-y", brain_slug="", cache=cache)
    # 空 slug 抛 ValueError → 不应 bump(否则连验证失败也污染计数器)
    assert cache.version("cryo") == v_before
    # loaded 标记保持(未走 invalidate 路径)
    assert cache.is_loaded("cryo") is True
