import pytest

from praxis2.memory.extract import ExtractCandidate, persist_candidates
from praxis2.memory.review import BrainCacheRegistry, approve
from praxis2.store.base import Namespace
from praxis2.store.memory import InMemoryStore


def _ns() -> Namespace:
    return Namespace(user_id="u1", scope="session")


def test_bump_increments_version_and_clears_loaded():

    cache = BrainCacheRegistry()
    cache.mark_loaded("cryo")
    assert cache.is_loaded("cryo") is True
    v0 = cache.version("cryo")
    new_v = cache.bump("cryo")
    assert new_v == v0 + 1
    assert cache.is_loaded("cryo") is False


def test_version_starts_at_zero_for_unknown_slug():

    cache = BrainCacheRegistry()
    assert cache.version("never_seen") == 0


def test_invalidate_legacy_api_still_bumps_version():

    cache = BrainCacheRegistry()
    v0 = cache.version("cryo")
    cache.invalidate("cryo")
    assert cache.version("cryo") == v0 + 1


def test_bump_multiple_times_monotonic():

    cache = BrainCacheRegistry()
    cache.bump("cryo")
    cache.bump("cryo")
    cache.bump("cryo")
    assert cache.version("cryo") == 3


async def test_approve_bumps_version_before_put_brain_doc(monkeypatch):

    cache = BrainCacheRegistry()
    cache.mark_loaded("cryo")
    v_before = cache.version("cryo")

    store = InMemoryStore()
    ns = _ns()
    await persist_candidates(
        store,
        ns,
        [
            ExtractCandidate(id="cand-1", text="bump-before-put \u6d4b\u8bd5", trigger="manual"),
        ],
    )

    from praxis2.memory import review as review_mod

    orig_put = review_mod.put_brain_doc
    version_at_put: list[int] = []

    async def spy_put(store_, user_id, doc):
        version_at_put.append(cache.version("cryo"))
        await orig_put(store_, user_id, doc)

    monkeypatch.setattr(review_mod, "put_brain_doc", spy_put)

    await approve(store, ns, "cand-1", brain_slug="cryo", cache=cache)

    assert version_at_put == [v_before + 1]

    assert cache.is_loaded("cryo") is False


async def test_approve_without_cache_no_version_tracking_no_crash():

    store = InMemoryStore()
    ns = _ns()
    await persist_candidates(
        store,
        ns,
        [
            ExtractCandidate(id="cand-x", text="\u65e0 cache \u8def\u5f84", trigger="manual"),
        ],
    )

    await approve(store, ns, "cand-x", brain_slug="cryo")


async def test_approve_empty_slug_does_not_bump_version():

    cache = BrainCacheRegistry()
    cache.mark_loaded("cryo")
    v_before = cache.version("cryo")
    store = InMemoryStore()
    ns = _ns()
    await persist_candidates(
        store,
        ns,
        [
            ExtractCandidate(id="cand-y", text="\u4e0d\u8be5 bump \u7684", trigger="manual"),
        ],
    )
    with pytest.raises(ValueError, match="must not be empty"):
        await approve(store, ns, "cand-y", brain_slug="", cache=cache)

    assert cache.version("cryo") == v_before

    assert cache.is_loaded("cryo") is True
