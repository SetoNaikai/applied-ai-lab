"""Deterministic retrieval metrics.

Measure retrieval in isolation BEFORE reaching for an LLM judge. These are
free, instant, and reproducible -- if retrieval is broken, no amount of
generation tuning will save the answer.
"""

from __future__ import annotations

import math


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    if k <= 0:
        return 0.0
    top = retrieved[:k]
    if not top:
        return 0.0
    return sum(1 for d in top if d in set(relevant)) / len(top)


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    if not relevant:
        return 1.0  # nothing to find; vacuously satisfied
    return sum(1 for d in retrieved[:k] if d in set(relevant)) / len(set(relevant))


def mrr(retrieved: list[str], relevant: list[str]) -> float:
    """Reciprocal rank of the first relevant hit."""
    relevant_set = set(relevant)
    for i, doc in enumerate(retrieved, start=1):
        if doc in relevant_set:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    relevant_set = set(relevant)
    dcg = sum(
        1.0 / math.log2(i + 1)
        for i, doc in enumerate(retrieved[:k], start=1)
        if doc in relevant_set
    )
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(relevant_set), k) + 1))
    return dcg / ideal if ideal else 0.0


def latency_percentiles(samples: list[float]) -> dict[str, float]:
    """p50/p95/p99. Report percentiles, not means -- means hide tail latency."""
    if not samples:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
    ordered = sorted(samples)

    def pct(p: float) -> float:
        idx = min(int(math.ceil(p / 100 * len(ordered))) - 1, len(ordered) - 1)
        return round(ordered[max(idx, 0)], 4)

    return {"p50": pct(50), "p95": pct(95), "p99": pct(99)}
