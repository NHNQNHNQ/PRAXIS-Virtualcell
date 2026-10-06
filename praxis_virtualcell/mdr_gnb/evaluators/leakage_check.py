"""泄漏断言:任一 ST/克隆群不得跨 train/test(G1 pytest 依赖此)。"""
from __future__ import annotations

from .lineage_split import SplitSpec


class LineageLeakError(AssertionError):
    """train/test 间存在同一 ST(克隆群)跨集,视为谱系泄漏。"""


def assert_no_lineage_leak(spec: SplitSpec, st_map: dict[str, str]) -> None:
    """断言单个 SplitSpec 无 ST 泄漏;违反抛 LineageLeakError。"""
    train_st = {st_map.get(g) for g in spec.train_ids}
    test_st = {st_map.get(g) for g in spec.test_ids}
    train_st.discard(None)
    test_st.discard(None)
    overlap = train_st & test_st
    if overlap:
        raise LineageLeakError(
            f"fold {spec.fold} 谱系泄漏:train/test 共享 ST {sorted(overlap)}"
        )


def assert_no_leak_all(specs: list[SplitSpec], st_map: dict[str, str]) -> None:
    """对全部 fold 逐一断言无泄漏。"""
    for spec in specs:
        assert_no_lineage_leak(spec, st_map)
