"""admin pagination helper — clamp + 类型转换。"""
from __future__ import annotations

import pytest

from praxis2.admin.repo import clamp_pagination


@pytest.mark.parametrize("page,limit,expect", [
    (1, 50, (1, 50)),
    ("1", "50", (1, 50)),
    (0, 50, (1, 50)),
    (-5, 50, (1, 50)),
    (1, 0, (1, 1)),
    (1, -5, (1, 1)),
    (1, 10000, (1, 200)),
    (None, None, (1, 50)),
    ("bad", "bad", (1, 50)),
])
def test_clamp_pagination(page, limit, expect):
    assert clamp_pagination(page, limit) == expect
