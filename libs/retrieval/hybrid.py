"""Reciprocal Rank Fusion.

Deliberately hand-written rather than imported. It is fifteen lines, and
understanding it is the difference between debugging a production retrieval
regression and shrugging at one.

RRF(d) = sum over result lists of 1 / (k + rank(d))
"""

from __future__ import annotations

from collections import defaultdict


def reciprocal_rank_fusion(
    result_lists: list[list[str]],
    *,
    k: int = 60,
    weights: list[float] | None = None,
) -> list[tuple[str, float]]:
    """Fuse ranked ID lists into one ranking.

    `k` damps the influence of top ranks; 60 is the conventional default.
    `weights` lets you favour dense over lexical (or the reverse) once evals
    tell you which is carrying the retrieval.
    """
    if weights is None:
        weights = [1.0] * len(result_lists)
    if len(weights) != len(result_lists):
        raise ValueError("weights must match the number of result lists")

    scores: dict[str, float] = defaultdict(float)
    for results, weight in zip(result_lists, weights, strict=True):
        for rank, doc_id in enumerate(results, start=1):
            scores[doc_id] += weight / (k + rank)

    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
