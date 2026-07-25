"""Unit tests for deterministic library logic. No network, no API keys."""

from __future__ import annotations

import pytest

from libs.evals.dataset import EvalCase, GoldenDataset
from libs.evals.metrics import latency_percentiles, mrr, ndcg_at_k, precision_at_k, recall_at_k
from libs.llm import Budget, BudgetExceeded, estimate_cost
from libs.retrieval.chunking import ChunkStrategy, chunk_document
from libs.retrieval.hybrid import reciprocal_rank_fusion


class TestBudget:
    def test_charges_accumulate(self) -> None:
        budget = Budget(limit_usd=1.0)
        budget.charge(0.3)
        budget.charge(0.4)
        assert budget.calls == 2
        assert budget.spent_usd == pytest.approx(0.7)

    def test_raises_before_exceeding(self) -> None:
        budget = Budget(limit_usd=0.5)
        budget.charge(0.4)
        with pytest.raises(BudgetExceeded):
            budget.charge(0.2)
        # The rejected charge must not be recorded.
        assert budget.spent_usd == pytest.approx(0.4)

    def test_local_models_are_free(self) -> None:
        assert estimate_cost("llama3.1:8b", 10_000, 10_000) == 0.0
        assert estimate_cost("claude-sonnet-4-6", 1_000_000, 0) == pytest.approx(3.00)


class TestRetrievalMetrics:
    def test_precision_and_recall(self) -> None:
        retrieved = ["a", "b", "c", "d", "e"]
        relevant = ["a", "c", "z"]
        assert precision_at_k(retrieved, relevant, 5) == pytest.approx(0.4)
        assert recall_at_k(retrieved, relevant, 5) == pytest.approx(2 / 3)

    def test_mrr_uses_first_hit(self) -> None:
        assert mrr(["x", "y", "a"], ["a"]) == pytest.approx(1 / 3)
        assert mrr(["x", "y"], ["a"]) == 0.0

    def test_ndcg_perfect_ranking_is_one(self) -> None:
        assert ndcg_at_k(["a", "b"], ["a", "b"], 2) == pytest.approx(1.0)

    def test_empty_relevant_set_is_vacuously_satisfied(self) -> None:
        assert recall_at_k(["a"], [], 5) == 1.0

    def test_latency_percentiles(self) -> None:
        pcts = latency_percentiles([0.1 * i for i in range(1, 101)])
        assert pcts["p50"] < pcts["p95"] < pcts["p99"]


class TestRRF:
    def test_document_in_both_lists_outranks_singletons(self) -> None:
        dense = ["a", "b", "c"]
        lexical = ["c", "d", "a"]
        fused = reciprocal_rank_fusion([dense, lexical])
        assert fused[0][0] == "a"
        assert {doc for doc, _ in fused} == {"a", "b", "c", "d"}

    def test_weights_shift_ranking(self) -> None:
        dense, lexical = ["a"], ["b"]
        assert reciprocal_rank_fusion([dense, lexical], weights=[10.0, 1.0])[0][0] == "a"
        assert reciprocal_rank_fusion([dense, lexical], weights=[1.0, 10.0])[0][0] == "b"

    def test_mismatched_weights_rejected(self) -> None:
        with pytest.raises(ValueError, match="weights must match"):
            reciprocal_rank_fusion([["a"], ["b"]], weights=[1.0])


class TestChunking:
    def test_produces_indexed_chunks(self) -> None:
        text = "\n\n".join(f"Paragraph {i}. " + "filler words here. " * 40 for i in range(6))
        chunks = chunk_document(text, strategy=ChunkStrategy.RECURSIVE, target_tokens=128)
        assert len(chunks) > 1
        assert [c.index for c in chunks] == list(range(len(chunks)))
        assert all(c.token_count > 0 for c in chunks)

    def test_strategy_recorded_in_metadata(self) -> None:
        chunks = chunk_document("short text", strategy=ChunkStrategy.PARAGRAPH)
        assert chunks[0].metadata["chunk_strategy"] == "paragraph"


class TestGoldenDataset:
    def test_health_check_flags_thin_dataset(self) -> None:
        ds = GoldenDataset(
            name="t",
            version="0.1.0",
            cases=[EvalCase(id=str(i), question="q?") for i in range(10)],
        )
        health = ds.health_check()
        warnings = " ".join(str(w) for w in health["warnings"])  # type: ignore[arg-type]
        assert "only 10 cases" in warnings
        assert "unanswerable" in warnings

    def test_roundtrip(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        ds = GoldenDataset(
            name="t",
            version="1.0.0",
            cases=[EvalCase(id="1", question="q?", unanswerable=True, category="unanswerable")],
        )
        path = tmp_path / "d.jsonl"
        ds.save(path)
        loaded = GoldenDataset.load(path)
        assert loaded.version == "1.0.0"
        assert loaded.cases[0].unanswerable is True

    def test_filter_by_unanswerable(self) -> None:
        ds = GoldenDataset(
            name="t",
            version="1",
            cases=[
                EvalCase(id="1", question="a?"),
                EvalCase(id="2", question="b?", unanswerable=True),
            ],
        )
        assert len(ds.filter(unanswerable=True)) == 1
