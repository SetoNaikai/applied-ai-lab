"""Eval runner: executes a system under test against a golden dataset.

Every project defines an async callable
    (question: str) -> tuple[answer, retrieved_doc_ids, context]
and hands it to `EvalRunner`. That keeps the harness identical across P1-P7,
which is what makes results comparable and the repo read as a platform.
"""

from __future__ import annotations

import asyncio
import subprocess
import time
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field

from libs.evals.dataset import EvalCase, GoldenDataset
from libs.evals.judge import FAITHFULNESS_RUBRIC, REFUSAL_RUBRIC, LLMJudge
from libs.evals.metrics import latency_percentiles, mrr, ndcg_at_k, precision_at_k, recall_at_k
from libs.llm import Budget

# (answer_text, retrieved_doc_ids, context_used)
SystemUnderTest = Callable[[str], Awaitable[tuple[str, list[str], str]]]


class CaseResult(BaseModel):
    case_id: str
    question: str
    answer: str
    retrieved: list[str] = Field(default_factory=list)
    latency_s: float = 0.0
    precision_at_5: float = 0.0
    recall_at_5: float = 0.0
    mrr: float = 0.0
    ndcg_at_5: float = 0.0
    judge_verdict: str | None = None
    judge_score: float | None = None
    judge_reasoning: str | None = None
    error: str | None = None


class EvalResult(BaseModel):
    project: str
    dataset: str
    dataset_version: str
    config: dict[str, Any] = Field(default_factory=dict)
    cases: list[CaseResult] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    total_cost_usd: float = 0.0
    git_sha: str | None = None

    def summary_table(self) -> str:
        lines = [f"{self.project} | {self.dataset} v{self.dataset_version}", "-" * 52]
        for key, value in self.metrics.items():
            rendered = f"{value:.3f}" if isinstance(value, float) else str(value)
            lines.append(f"{key:<34} {rendered:>16}")
        lines.append("-" * 52)
        lines.append(f"{'total cost (USD)':<34} {self.total_cost_usd:>16.4f}")
        return "\n".join(lines)


def _git_sha() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


class EvalRunner:
    def __init__(
        self,
        project: str,
        dataset: GoldenDataset,
        *,
        judge_model: str | None = None,
        budget_usd: float | None = None,
        concurrency: int = 4,
    ) -> None:
        self.project = project
        self.dataset = dataset
        self.concurrency = concurrency
        self.budget = Budget(limit_usd=budget_usd) if budget_usd else None
        self.faithfulness_judge = LLMJudge(
            FAITHFULNESS_RUBRIC, model=judge_model, budget=self.budget
        )
        self.refusal_judge = LLMJudge(REFUSAL_RUBRIC, model=judge_model, budget=self.budget)

    async def run(
        self,
        system: SystemUnderTest,
        *,
        config: dict[str, Any] | None = None,
        judge: bool = True,
    ) -> EvalResult:
        semaphore = asyncio.Semaphore(self.concurrency)

        async def one(case: EvalCase) -> CaseResult:
            async with semaphore:
                return await self._run_case(case, system, judge=judge)

        cases = await asyncio.gather(*(one(c) for c in self.dataset.cases))
        result = EvalResult(
            project=self.project,
            dataset=self.dataset.name,
            dataset_version=self.dataset.version,
            config=config or {},
            cases=list(cases),
            total_cost_usd=self.budget.spent_usd if self.budget else 0.0,
            git_sha=_git_sha(),
        )
        result.metrics = self._aggregate(result.cases)
        return result

    async def _run_case(
        self, case: EvalCase, system: SystemUnderTest, *, judge: bool
    ) -> CaseResult:
        started = time.perf_counter()
        try:
            answer, retrieved, context = await system(case.question)
        except Exception as exc:  # noqa: BLE001 - a crash is an eval result, not a stop
            return CaseResult(
                case_id=case.id,
                question=case.question,
                answer="",
                latency_s=time.perf_counter() - started,
                error=f"{type(exc).__name__}: {exc}",
            )

        result = CaseResult(
            case_id=case.id,
            question=case.question,
            answer=answer,
            retrieved=retrieved,
            latency_s=time.perf_counter() - started,
            precision_at_5=precision_at_k(retrieved, case.relevant_doc_ids, 5),
            recall_at_5=recall_at_k(retrieved, case.relevant_doc_ids, 5),
            mrr=mrr(retrieved, case.relevant_doc_ids),
            ndcg_at_5=ndcg_at_k(retrieved, case.relevant_doc_ids, 5),
        )

        if judge:
            # Unanswerable cases are graded on refusal, not faithfulness.
            active = self.refusal_judge if case.unanswerable else self.faithfulness_judge
            verdict = await active.grade(
                question=case.question,
                answer=answer,
                context=context,
                expected=case.expected_answer,
            )
            result.judge_verdict = verdict.verdict
            result.judge_score = verdict.score
            result.judge_reasoning = verdict.reasoning

        return result

    def _aggregate(self, cases: list[CaseResult]) -> dict[str, Any]:
        ok = [c for c in cases if c.error is None]
        judged = [c for c in ok if c.judge_score is not None]
        answerable = [
            c
            for c in judged
            if not next(x.unanswerable for x in self.dataset.cases if x.id == c.case_id)
        ]
        unanswerable = [
            c
            for c in judged
            if next(x.unanswerable for x in self.dataset.cases if x.id == c.case_id)
        ]

        def mean(values: list[float]) -> float:
            return round(sum(values) / len(values), 4) if values else 0.0

        metrics: dict[str, Any] = {
            "n_cases": len(cases),
            "n_errors": len(cases) - len(ok),
            "precision@5": mean([c.precision_at_5 for c in ok]),
            "recall@5": mean([c.recall_at_5 for c in ok]),
            "mrr": mean([c.mrr for c in ok]),
            "ndcg@5": mean([c.ndcg_at_5 for c in ok]),
            "faithfulness": mean([c.judge_score or 0.0 for c in answerable]),
            "refusal_accuracy": mean([c.judge_score or 0.0 for c in unanswerable]),
            "pass_rate": mean([1.0 if c.judge_verdict == "pass" else 0.0 for c in judged]),
        }
        metrics.update(
            {f"latency_{k}": v for k, v in latency_percentiles([c.latency_s for c in ok]).items()}
        )
        return metrics
