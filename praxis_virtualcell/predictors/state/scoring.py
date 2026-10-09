"""Shared plain-Python marker scoring for committed raw-count subsets. Normalize CP10k+log1p, subtract housekeeping
means from panel means, and calculate group Cohen's d without scanpy/NumPy.
"""
from __future__ import annotations

import math


def lognorm(counts, total_counts, target: float = 1e4) -> list[float]:
    """Normalize counts to the target library size and apply log1p."""
    tot = total_counts or 1.0
    return [math.log1p(c / tot * target) for c in counts]


def panel_score(ln: list[float], panel_idx: list[int], hk_idx: list[int]) -> float | None:
    """Return panel mean minus housekeeping mean; an empty panel or housekeeping set returns None."""
    if not panel_idx or not hk_idx:
        return None
    return sum(ln[i] for i in panel_idx) / len(panel_idx) - sum(ln[i] for i in hk_idx) / len(hk_idx)


def cohens_d(a: list[float], b: list[float]) -> float:
    """Return mean difference divided by pooled standard deviation; either group with fewer than 2 observations
    returns 0.
    """
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return 0.0
    ma, mb = sum(a) / na, sum(b) / nb
    va = sum((x - ma) ** 2 for x in a) / (na - 1)
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1)
    psd = math.sqrt((va + vb) / 2) or 1e-9
    return (ma - mb) / psd
