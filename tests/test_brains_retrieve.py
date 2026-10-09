from praxis2.brains.migrate import build_fixture_brain
from praxis2.brains.retrieve import RetrievalResult, retrieve_brain


def test_keyword_overlap_ranks_relevant_doc_first():
    docs = [
        type(
            "D",
            (),
            {
                "slug": "Cryo",
                "kind": "cases",
                "stem": "c1",
                "text": "\u51b7\u51bb\u7535\u955c \u9897\u7c92\u6311\u9009 \u4e09\u7ef4\u91cd\u6784",
            },
        )(),
        type(
            "D",
            (),
            {
                "slug": "Cryo",
                "kind": "cases",
                "stem": "c2",
                "text": "\u9176\u52a8\u529b\u5b66 \u7c73\u6c0f\u65b9\u7a0b",
            },
        )(),
    ]
    r = retrieve_brain(docs, "\u51b7\u51bb\u7535\u955c \u4e09\u7ef4\u91cd\u6784\u600e\u4e48\u505a", top_k=1)
    assert isinstance(r, RetrievalResult)
    assert r.degraded_to_bare is False
    assert len(r.hits) == 1
    assert r.hits[0].stem == "c1"


def test_no_overlap_yields_degraded_to_bare_explicit_not_silent():
    docs = build_fixture_brain("Cryo")
    r = retrieve_brain(docs, "\u5b8c\u5168\u65e0\u5173\u7684\u70f9\u996a\u98df\u8c31\u5185\u5bb9", top_k=3)
    assert r.degraded_to_bare is True
    assert r.hits == []
    assert "Retrieval fallback" in r.reason or "bare" in r.reason


def test_empty_docs_degrades_to_bare():
    r = retrieve_brain([], "\u4efb\u4f55\u67e5\u8be2", top_k=3)
    assert r.degraded_to_bare is True and r.hits == []


def test_top_k_caps_hits():
    docs = build_fixture_brain("Enzyme")
    r = retrieve_brain(docs, "Enzyme \u9886\u57df Rule \u6280\u80fd \u6b63\u4f8b \u53cd\u4f8b", top_k=2)
    assert len(r.hits) <= 2
    assert r.degraded_to_bare is False
