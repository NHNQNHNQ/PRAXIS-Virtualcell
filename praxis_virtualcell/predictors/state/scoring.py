"""W5(v0.4):scRNA marker-based 评分共享 helper —— cell-state(ISG)与 metabolic tendency 复用。

纯 Python(不依赖 scanpy/numpy),供 committed 子集(原始 counts)上的确定性评分:
CP10k+log1p 归一 → panel 均值 − housekeeping 均值 → 组间 Cohen's d。
"""
from __future__ import annotations

import math


def lognorm(counts, total_counts, target: float = 1e4) -> list[float]:
    """CP(target)+log1p 归一。"""
    tot = total_counts or 1.0
    return [math.log1p(c / tot * target) for c in counts]


def panel_score(ln: list[float], panel_idx: list[int], hk_idx: list[int]) -> float | None:
    """panel 均值 − housekeeping 均值(相对活性评分)。panel/hk 任一空 → None。"""
    if not panel_idx or not hk_idx:
        return None
    return sum(ln[i] for i in panel_idx) / len(panel_idx) - sum(ln[i] for i in hk_idx) / len(hk_idx)


def cohens_d(a: list[float], b: list[float]) -> float:
    """两组均值差 / pooled sd。任一组 <2 → 0。"""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return 0.0
    ma, mb = sum(a) / na, sum(b) / nb
    va = sum((x - ma) ** 2 for x in a) / (na - 1)
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1)
    psd = math.sqrt((va + vb) / 2) or 1e-9
    return (ma - mb) / psd
