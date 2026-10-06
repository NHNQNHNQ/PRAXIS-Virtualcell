"""跨物种筛选:候选排序 + 广谱/窄谱/逃逸风险热图(G5)。"""
from __future__ import annotations


def rank_candidates(results: list) -> list:
    """按跨物种活性/风险对候选药物排序。M5 实现。"""
    raise NotImplementedError("M5 实现:候选排序 + 实验优先级")


def build_heatmap(results: list) -> dict:
    """构建物种×候选活性热图数据结构。M5 实现。"""
    raise NotImplementedError("M5 实现:跨物种活性热图")
