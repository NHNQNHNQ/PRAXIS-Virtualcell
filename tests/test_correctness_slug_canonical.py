def test_disciplines_are_lowercase_and_single_virtualcell():

    from praxis2.brains.migrate import DISCIPLINE_SLUGS

    assert len(DISCIPLINE_SLUGS) == 1
    assert all(s == s.lower() for s in DISCIPLINE_SLUGS), (
        f"Brain identifiers must be lowercase; observed:{DISCIPLINE_SLUGS}"
    )
    assert "virtualcell" in DISCIPLINE_SLUGS, (
        "PRAXIS-virtualcell \u5355\u4e00\u5927\u8111\u5fc5\u987b\u662f virtualcell"
    )


def test_slug_constants_aligned_across_modules():

    from praxis2.agents.loader import _SLUG_KEYWORDS
    from praxis2.brains.migrate import _SLUG_CASE_HINTS, DISCIPLINE_SLUGS
    from scripts.migrate_brains import _LEGACY_SLUGS

    expected = set(DISCIPLINE_SLUGS)
    assert set(_LEGACY_SLUGS) == expected, "scripts.migrate_brains._LEGACY_SLUGS \u6f02\u79fb"
    assert set(_SLUG_KEYWORDS.keys()) == expected, "agents.loader._SLUG_KEYWORDS \u6f02\u79fb"
    assert set(_SLUG_CASE_HINTS.keys()) == expected, "brains.migrate._SLUG_CASE_HINTS \u6f02\u79fb"


def test_resolve_agent_normalizes_input_case():

    from praxis2.agents.loader import resolve_agent

    sel_lower = resolve_agent("virtualcell", user_query="perturbation")
    sel_title = resolve_agent("Virtualcell", user_query="perturbation")
    sel_upper = resolve_agent("VIRTUALCELL", user_query="perturbation")

    assert sel_lower.brain_slugs == sel_title.brain_slugs == sel_upper.brain_slugs
    assert sel_lower.brain_slugs == ["_common", "virtualcell"]
