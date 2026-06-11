"""RRF (Reciprocal Rank Fusion) with channel weights.

Standard formula: score(item) = Σ_channel w_channel / (k + rank_channel(item))
where k=60 is the canonical RRF constant.

This is more robust than weighted-sum-of-scores because it doesn't require
score normalization across channels with different scales (BM25 vs cosine vs
binary tag match).
"""

from __future__ import annotations


def rrf(
    rankings: dict[str, list[str]],
    weights: dict[str, float] | None = None,
    k: int = 60,
) -> list[tuple[str, float]]:
    """Fuse rankings from multiple channels.

    Args:
        rankings: {channel_name: ordered_list_of_item_ids}
        weights: {channel_name: weight}. Default: 1.0 per channel.
        k: RRF constant (default 60).

    Returns:
        Ordered list of (item_id, fused_score), highest score first.
    """
    if weights is None:
        weights = {ch: 1.0 for ch in rankings}
    scores: dict[str, float] = {}
    for channel, ranked in rankings.items():
        w = weights.get(channel, 0.0)
        if w == 0:
            continue
        for rank, item_id in enumerate(ranked, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + w / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])


if __name__ == "__main__":
    rankings = {
        "family":   ["case_A", "case_B", "case_C"],
        "ec":       ["case_B", "case_A", "case_C"],
        "text":     ["case_C", "case_A", "case_B"],
    }
    weights = {"family": 2.0, "ec": 1.0, "text": 0.5}
    for item, score in rrf(rankings, weights):
        print(f"  {item:10} {score:.5f}")
