"""Bug carry(2026-05-31 FE smoke):FE STATUS_LABEL = pending/shipped/promoted/held/rejected
与后端真实 (status='open'/'decided', admin_verdict, shipped_to) 二元组不对齐
→ 两处 FE(ProposalsModal / AdminPanel)的 status 列都 fallback 到原始字串 'open'。

修法:后端 repo.py 加 _derive_display_status,_row_to_dict 与 _admin_row_to_dict
都补 'display_status' 字段。FE 改 p.status → p.display_status ?? p.status。

本测试覆盖 derive 函数 5 映射 + unknown fallback 共 6 用例。
"""
from __future__ import annotations

import pytest

from praxis2.proposals.repo import _derive_display_status


@pytest.mark.parametrize(("status", "verdict", "shipped_to", "expected"), [
    # 1. 未决:status=open → 始终 pending(verdict 应为 None)
    ("open", None, None, "pending"),
    # 2. 已决 + ship + 未 promote → shipped
    ("decided", "ship", None, "shipped"),
    # 3. 已决 + ship + 已 promote(shipped_to 非空) → promoted(更强语义)
    ("decided", "ship", "brains/microbiome", "promoted"),
    # 4. 已决 + hold → held
    ("decided", "hold", None, "held"),
    # 5. 已决 + reject → rejected
    ("decided", "reject", None, "rejected"),
    # 6. 未预期组合(decided + verdict 缺失)→ fallback pending(保守,FE 走 KEY 命中)
    ("decided", None, None, "pending"),
])
def test_derive_display_status_5_mappings_plus_fallback(status, verdict, shipped_to, expected):
    assert _derive_display_status(status, verdict, shipped_to) == expected
