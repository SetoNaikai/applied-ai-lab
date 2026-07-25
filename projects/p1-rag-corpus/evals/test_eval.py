"""P1 eval suite. Runs against the golden dataset, gated in CI.

The system-under-test signature is fixed by `libs.evals.EvalRunner`:
    async (question) -> (answer, retrieved_doc_ids, context)

Keeping that contract identical across P1-P7 is what makes results comparable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from libs.evals import EvalRunner, GoldenDataset

DATASET = Path(__file__).parent / "dataset.jsonl"

# Thresholds. These are meant to fail when quality regresses.
# Do NOT loosen them to make a build pass -- fix the regression, or write an ADR
# explaining why the threshold was wrong. See AGENTS.md (Evaluation rules).
THRESHOLDS = {
    "recall@5": 0.70,
    "faithfulness": 0.80,
    "refusal_accuracy": 0.75,
}


@pytest.fixture
def dataset() -> GoldenDataset:
    if not DATASET.exists():
        pytest.skip("golden dataset not yet built in P2 -- see projects/p2-eval-harness/README.md")
    return GoldenDataset.load(DATASET)


def test_dataset_is_healthy(dataset: GoldenDataset) -> None:
    """A suite built on a bad dataset produces numbers not worth reporting."""
    health = dataset.health_check()
    assert not health["warnings"], f"dataset health warnings: {health['warnings']}"


@pytest.mark.eval
@pytest.mark.costs_money
async def test_rag_meets_thresholds(dataset: GoldenDataset) -> None:
    from projects.p1_rag_corpus.pipeline import answer_question  # noqa: PLC0415

    runner = EvalRunner("p1-rag-corpus", dataset, budget_usd=5.00)
    result = await runner.run(answer_question, config={"retrieval": "hybrid", "k": 5})

    print("\n" + result.summary_table())

    failures = [
        f"{metric}: {result.metrics[metric]:.3f} < {floor:.2f}"
        for metric, floor in THRESHOLDS.items()
        if result.metrics.get(metric, 0.0) < floor
    ]
    assert not failures, "eval regression:\n  " + "\n  ".join(failures)
