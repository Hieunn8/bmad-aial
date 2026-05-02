"""Reciprocal Rank Fusion — Story 3.3.

k=60 (default) following the RRF paper (Cormack et al. 2009).
score(d) = Σ 1 / (k + rank(d, list_i))
"""

from __future__ import annotations


def reciprocal_rank_fusion(
    *result_lists: list[dict],
    k: int = 60,
    id_key: str = "id",
) -> list[dict]:
    """Merge multiple ranked result lists using RRF.

    Each item in each list must have an `id_key` field.
    Returns merged list sorted by descending RRF score.
    """
    scores: dict[str, float] = {}
    item_map: dict[str, dict] = {}

    for result_list in result_lists:
        for rank, item in enumerate(result_list, start=1):
            item_id = item[id_key]
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            item_map.setdefault(item_id, item)

    merged = [
        {**item_map[item_id], "rrf_score": score}
        for item_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
    ]
    return merged
