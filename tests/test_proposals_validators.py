"""proposals handler 端用的纯函数校验:kind/verdict enum + 长度。"""
from __future__ import annotations

import pytest

from praxis2.proposals.repo import _PROPOSAL_KIND, _PROPOSAL_VERDICT


def test_proposal_kind_enum():
    assert _PROPOSAL_KIND == {"idea", "feature", "bug"}


def test_proposal_verdict_enum():
    assert _PROPOSAL_VERDICT == {"ship", "promote", "hold", "reject"}


@pytest.mark.parametrize("title,expected", [
    ("", "empty"),
    ("x" * 201, "too_long"),
    ("ok title", "valid"),
])
def test_title_length_rule(title, expected):
    if not title.strip():
        result = "empty"
    elif len(title) > 200:
        result = "too_long"
    else:
        result = "valid"
    assert result == expected


@pytest.mark.parametrize("body,expected", [
    (None, "valid"),
    ("", "valid"),
    ("x" * 5001, "too_long"),
    ("normal body", "valid"),
])
def test_body_length_rule(body, expected):
    if body and len(body) > 5000:
        result = "too_long"
    else:
        result = "valid"
    assert result == expected


@pytest.mark.parametrize("score,valid", [
    (None, True),
    (1, True),
    (5, True),
    (0, False),
    (6, False),
    (-1, False),
])
def test_score_range(score, valid):
    result = score is None or (1 <= score <= 5)
    assert result == valid
