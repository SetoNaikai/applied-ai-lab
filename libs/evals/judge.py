"""LLM-as-judge with explicit rubrics.

The step almost everyone skips: VALIDATING the judge. An unvalidated judge is
just a second unmeasured model. `LLMJudge.agreement()` compares judge verdicts
against your own labels on a sample so you can report an actual agreement rate.

Doing this is a strong senior signal in interviews. Have the number ready.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from libs.llm import LLM, Budget

Verdict = Literal["pass", "fail", "partial"]

FAITHFULNESS_RUBRIC = """\
You are grading whether an ANSWER is fully supported by the provided CONTEXT.

pass    - every factual claim in the answer is directly supported by the context
partial - the answer is mostly supported but contains at least one unsupported claim
fail    - the answer contains claims contradicted by or absent from the context

Ignore style, tone, and completeness. Judge support only.
"""

REFUSAL_RUBRIC = """\
You are grading whether the system correctly DECLINED to answer.

The context does not contain the information needed. Correct behaviour is to
say so plainly.

pass    - clearly states the information is unavailable, and asserts no facts
partial - hedges but still asserts unsupported facts
fail    - answers confidently as though the information were present
"""

KOREAN_GRAMMAR_RUBRIC = """\
You are grading a Korean language learner's answer (TOPIK I level).

Classify every error by type, using exactly these labels:
  vocabulary, particle, conjugation, word_order, honorific, spelling

pass    - no errors, or one trivial spelling slip
partial - comprehensible but with 1-2 grammatical errors
fail    - meaning is unclear or there are 3+ errors

Be encouraging in `reasoning`, but strict in `verdict` and complete in `errors`.
"""


class JudgeResult(BaseModel):
    verdict: Verdict
    score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    errors: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)


class LLMJudge:
    def __init__(
        self,
        rubric: str = FAITHFULNESS_RUBRIC,
        *,
        model: str | None = None,
        budget: Budget | None = None,
    ) -> None:
        self.rubric = rubric
        self.llm = LLM(model=model, temperature=0.0, budget=budget)

    async def grade(
        self,
        *,
        question: str,
        answer: str,
        context: str | None = None,
        expected: str | None = None,
    ) -> JudgeResult:
        parts = [f"QUESTION:\n{question}", f"ANSWER:\n{answer}"]
        if context:
            parts.append(f"CONTEXT:\n{context}")
        if expected:
            parts.append(f"REFERENCE ANSWER:\n{expected}")

        system = (
            f"{self.rubric}\n\n"
            "Respond with ONLY a JSON object, no markdown fences, no preamble:\n"
            '{"verdict": "pass|partial|fail", "score": 0.0-1.0, '
            '"reasoning": "one or two sentences", "errors": [], '
            '"unsupported_claims": []}'
        )
        out = await self.llm.complete("\n\n".join(parts), system=system)
        return self._parse(out.text)

    @staticmethod
    def _parse(text: str) -> JudgeResult:
        cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        try:
            return JudgeResult.model_validate(json.loads(cleaned.strip()))
        except (json.JSONDecodeError, ValueError) as exc:
            # A judge that fails to parse must not silently become a pass.
            return JudgeResult(
                verdict="fail",
                score=0.0,
                reasoning=f"judge output unparseable: {exc}",
                errors=["judge_parse_error"],
            )

    async def agreement(
        self,
        samples: list[dict[str, str]],
        human_labels: list[Verdict],
    ) -> dict[str, object]:
        """Validate the judge against your own labels.

        Sample ~30 cases, grade them yourself, run this. Report the number.
        Below roughly 0.8 agreement, tighten the rubric before trusting any
        score the judge produces.
        """
        if len(samples) != len(human_labels):
            raise ValueError("samples and human_labels must be the same length")

        verdicts: list[Verdict] = []
        for sample in samples:
            result = await self.grade(
                question=sample["question"],
                answer=sample["answer"],
                context=sample.get("context"),
            )
            verdicts.append(result.verdict)

        matches = sum(1 for a, b in zip(verdicts, human_labels, strict=True) if a == b)
        rate = matches / len(human_labels)
        return {
            "n": len(human_labels),
            "agreement_rate": round(rate, 3),
            "judge_verdicts": verdicts,
            "human_labels": human_labels,
            "acceptable": rate >= 0.80,
        }
