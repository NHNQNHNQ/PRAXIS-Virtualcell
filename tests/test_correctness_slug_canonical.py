"""B.3+ v2.0.2 不变式:slug 单源 lowercase 13 项,跨模块对齐(防回归 4 处漂移)。

reviewer M5 C1+C2:DISCIPLINE_SLUGS / _LEGACY_SLUGS / _SLUG_KEYWORDS / _SLUG_CASE_HINTS
四源历史各拼大小写,真盘 /Volumes/T7/PRAXIS-Brains/_brains/ 实为 lowercase 13 项
(v2.0.2 起 Synth carry 落地,brains/synth/ 已含 22 cases / 44 rules / 13 workflows)。
本不变式锁四源对齐 + resolve_agent 输入大小写标准化,防 retrieve 静默退化 bare。
"""


def test_disciplines_are_lowercase_and_13():
    from praxis2.brains.migrate import DISCIPLINE_SLUGS
    assert len(DISCIPLINE_SLUGS) == 13
    assert all(s == s.lower() for s in DISCIPLINE_SLUGS), \
        f"slug 必须 lowercase(真盘对齐),实际:{DISCIPLINE_SLUGS}"
    assert "synth" in DISCIPLINE_SLUGS, \
        "Synth v2.0.2 已落地(brains/synth/ + _brains/synth/),必须在 13 学科内"


def test_slug_constants_aligned_across_modules():
    """4 处源头全部对齐 13 项 lowercase(DISCIPLINE_SLUGS / _LEGACY_SLUGS /
    _SLUG_KEYWORDS / _SLUG_CASE_HINTS),防漂移再发生。"""
    from praxis2.agents.loader import _SLUG_KEYWORDS
    from praxis2.brains.migrate import _SLUG_CASE_HINTS, DISCIPLINE_SLUGS
    from scripts.migrate_brains import _LEGACY_SLUGS

    expected = set(DISCIPLINE_SLUGS)
    assert set(_LEGACY_SLUGS) == expected, "scripts.migrate_brains._LEGACY_SLUGS 漂移"
    assert set(_SLUG_KEYWORDS.keys()) == expected, "agents.loader._SLUG_KEYWORDS 漂移"
    assert set(_SLUG_CASE_HINTS.keys()) == expected, "brains.migrate._SLUG_CASE_HINTS 漂移"


def test_resolve_agent_normalizes_input_case():
    """resolve_agent('Cryo')、'CRYO'、'cryo' 全部命中同一 slug,
    且 brain_slugs 内统一 lowercase(对齐真盘 namespace brain:cryo)。"""
    from praxis2.agents.loader import resolve_agent
    sel_lower = resolve_agent("cryo", user_query="冷冻电镜")
    sel_title = resolve_agent("Cryo", user_query="冷冻电镜")
    sel_upper = resolve_agent("CRYO", user_query="冷冻电镜")
    # 三种大小写输入应导出同一 brain_slugs(全 lowercase)
    assert sel_lower.brain_slugs == sel_title.brain_slugs == sel_upper.brain_slugs
    assert sel_lower.brain_slugs == ["_common", "cryo"]
