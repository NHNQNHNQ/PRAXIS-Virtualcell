from praxis2.brains.migrate import build_fixture_brain
from praxis2.brains.retrieve import RetrievalResult, retrieve_brain


def test_keyword_overlap_ranks_relevant_doc_first():
    docs = [
        type("D", (), {"slug": "Cryo", "kind": "cases", "stem": "c1",
                       "text": "冷冻电镜 颗粒挑选 三维重构"})(),
        type("D", (), {"slug": "Cryo", "kind": "cases", "stem": "c2",
                       "text": "酶动力学 米氏方程"})(),
    ]
    r = retrieve_brain(docs, "冷冻电镜 三维重构怎么做", top_k=1)
    assert isinstance(r, RetrievalResult)
    assert r.degraded_to_bare is False
    assert len(r.hits) == 1
    assert r.hits[0].stem == "c1"


def test_no_overlap_yields_degraded_to_bare_explicit_not_silent():
    docs = build_fixture_brain("Cryo")
    r = retrieve_brain(docs, "完全无关的烹饪食谱内容", top_k=3)
    assert r.degraded_to_bare is True
    assert r.hits == []
    assert "降级" in r.reason or "bare" in r.reason  # 显式记录,不静默


def test_empty_docs_degrades_to_bare():
    r = retrieve_brain([], "任何查询", top_k=3)
    assert r.degraded_to_bare is True and r.hits == []


def test_top_k_caps_hits():
    docs = build_fixture_brain("Enzyme")  # 4 docs,均含 "Enzyme"
    r = retrieve_brain(docs, "Enzyme 领域 规则 技能 正例 反例", top_k=2)
    assert len(r.hits) <= 2
    assert r.degraded_to_bare is False
