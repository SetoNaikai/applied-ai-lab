"""Golden datasets.

The hard part of evaluation, and the part everyone skips.

Two rules that matter more than any metric implementation:
  1. Write cases from the SOURCE DOCUMENTS, never from retrieved chunks.
     Writing from chunks guarantees high scores that mean nothing.
  2. ~20% of cases must be UNANSWERABLE by the corpus. That subset is your
     hallucination test bed, and a system that correctly refuses is more
     valuable than one that always answers.

Datasets are versioned. Never edit a released version in place -- historical
eval runs must stay comparable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

Difficulty = Literal["easy", "medium", "hard"]
Category = Literal["lookup", "multi_hop", "aggregation", "temporal", "unanswerable"]


class EvalCase(BaseModel):
    id: str
    question: str
    expected_answer: str | None = None
    # Document/chunk ids that must be retrieved for a correct answer.
    relevant_doc_ids: list[str] = Field(default_factory=list)
    # Verbatim spans the answer should be grounded in.
    required_spans: list[str] = Field(default_factory=list)
    category: Category = "lookup"
    difficulty: Difficulty = "medium"
    # True when the corpus genuinely cannot answer -- correct behaviour is refusal.
    unanswerable: bool = False
    notes: str | None = None


class GoldenDataset(BaseModel):
    name: str
    version: str
    description: str = ""
    cases: list[EvalCase] = Field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path) -> GoldenDataset:
        path = Path(path)
        meta_path = path.with_suffix(".meta.json")
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        cases = [
            EvalCase.model_validate_json(line)
            for line in path.read_text().splitlines()
            if line.strip()
        ]
        return cls(
            name=meta.get("name", path.stem),
            version=meta.get("version", "0.0.0"),
            description=meta.get("description", ""),
            cases=cases,
        )

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(c.model_dump_json() for c in self.cases) + "\n")
        path.with_suffix(".meta.json").write_text(
            json.dumps(
                {"name": self.name, "version": self.version, "description": self.description},
                indent=2,
            )
        )

    def filter(
        self,
        *,
        category: Category | None = None,
        difficulty: Difficulty | None = None,
        unanswerable: bool | None = None,
    ) -> list[EvalCase]:
        cases = self.cases
        if category is not None:
            cases = [c for c in cases if c.category == category]
        if difficulty is not None:
            cases = [c for c in cases if c.difficulty == difficulty]
        if unanswerable is not None:
            cases = [c for c in cases if c.unanswerable is unanswerable]
        return cases

    def health_check(self) -> dict[str, object]:
        """Run this before trusting any score from this dataset."""
        n = len(self.cases)
        unanswerable = len(self.filter(unanswerable=True))
        by_category = {c.category: 0 for c in self.cases}
        for c in self.cases:
            by_category[c.category] += 1
        warnings: list[str] = []
        if n < 50:
            warnings.append(f"only {n} cases -- results will be noisy; aim for 100+")
        share = unanswerable / n if n else 0
        if share < 0.10:
            warnings.append(
                f"unanswerable share is {share:.0%} -- target ~20% to test hallucination"
            )
        if len(by_category) < 3:
            warnings.append("fewer than 3 categories -- add multi_hop and temporal cases")
        return {
            "cases": n,
            "unanswerable": unanswerable,
            "by_category": by_category,
            "warnings": warnings,
        }
