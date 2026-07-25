"""Provider-agnostic LLM client.

Every model call in this repo goes through here. Reasons:
  1. One place to add tracing, retries, and cost accounting.
  2. Swapping local <-> frontier becomes a config change, which is what makes
     the P4 build-vs-buy comparison possible at all.
  3. Projects stay free of provider SDK imports.

Usage:
    llm = LLM()                                  # frontier default
    out = await llm.complete("Explain HNSW.")
    local = LLM(model="llama3.1:8b")             # routed to Ollama
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from libs.settings import get_settings

Role = Literal["system", "user", "assistant"]


class Message(BaseModel):
    role: Role
    content: str


class Completion(BaseModel):
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0
    raw: dict[str, Any] | None = None


class BudgetExceeded(RuntimeError):
    """Raised when a run would exceed its configured spend ceiling."""


@dataclass
class Budget:
    """Hard cost ceiling for a run.

    Any script that loops over LLM calls must use one of these. Discovering
    a $400 bill on Sunday morning is a rite of passage worth skipping.
    """

    limit_usd: float
    spent_usd: float = 0.0
    calls: int = 0
    _log: list[float] = field(default_factory=list)

    def charge(self, amount: float) -> None:
        if self.spent_usd + amount > self.limit_usd:
            raise BudgetExceeded(
                f"Run would exceed budget: ${self.spent_usd:.4f} + "
                f"${amount:.4f} > ${self.limit_usd:.2f} after {self.calls} calls"
            )
        self.spent_usd += amount
        self.calls += 1
        self._log.append(amount)

    def summary(self) -> dict[str, float | int]:
        return {
            "calls": self.calls,
            "spent_usd": round(self.spent_usd, 4),
            "limit_usd": self.limit_usd,
            "avg_call_usd": round(self.spent_usd / self.calls, 6) if self.calls else 0.0,
        }


# USD per 1M tokens (input, output). Verify against current provider pricing
# before quoting these in a write-up -- pricing changes.
PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Local models are free at the margin; that is the point of the comparison."""
    if model not in PRICING:
        return 0.0
    in_rate, out_rate = PRICING[model]
    return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000


class LLM:
    """Thin async wrapper. Routes to Ollama for local models, SDKs otherwise."""

    def __init__(
        self,
        model: str | None = None,
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        budget: Budget | None = None,
    ) -> None:
        self.settings = get_settings()
        self.model = model or self.settings.default_frontier_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.budget = budget

    @property
    def is_local(self) -> bool:
        return not (self.model.startswith(("claude-", "gpt-", "gemini-")))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=20))
    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        history: list[Message] | None = None,
    ) -> Completion:
        messages = [*(history or []), Message(role="user", content=prompt)]
        started = time.perf_counter()

        if self.is_local:
            result = await self._ollama(messages, system)
        elif self.model.startswith("claude-"):
            result = await self._anthropic(messages, system)
        elif self.model.startswith("gpt-"):
            result = await self._openai(messages, system)
        else:
            raise ValueError(f"No route for model {self.model!r}")

        result.latency_s = time.perf_counter() - started
        result.cost_usd = estimate_cost(self.model, result.input_tokens, result.output_tokens)
        if self.budget is not None:
            self.budget.charge(result.cost_usd)
        return result

    # ---- providers -------------------------------------------------------

    async def _anthropic(self, messages: list[Message], system: str | None) -> Completion:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [m.model_dump() for m in messages],
        }
        if system:
            kwargs["system"] = system
        resp = await client.messages.create(**kwargs)
        return Completion(
            text="".join(b.text for b in resp.content if b.type == "text"),
            model=self.model,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )

    async def _openai(self, messages: list[Message], system: str | None) -> Completion:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        payload = [m.model_dump() for m in messages]
        if system:
            payload.insert(0, {"role": "system", "content": system})
        resp = await client.chat.completions.create(
            model=self.model,
            messages=payload,  # type: ignore[arg-type]
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        usage = resp.usage
        return Completion(
            text=resp.choices[0].message.content or "",
            model=self.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )

    async def _ollama(self, messages: list[Message], system: str | None) -> Completion:
        payload = [m.model_dump() for m in messages]
        if system:
            payload.insert(0, {"role": "system", "content": system})
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{self.settings.ollama_base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": payload,
                    "stream": False,
                    "options": {"temperature": self.temperature},
                },
            )
            resp.raise_for_status()
            data = resp.json()
        return Completion(
            text=data["message"]["content"],
            model=self.model,
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            raw=data,
        )


async def embed(texts: list[str], model: str | None = None) -> list[list[float]]:
    """Embeddings via Ollama. Dimension must match the vector(n) column."""
    settings = get_settings()
    model = model or settings.embedding_model
    out: list[list[float]] = []
    async with httpx.AsyncClient(timeout=300) as client:
        for text in texts:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/embeddings",
                json={"model": model, "prompt": text},
            )
            resp.raise_for_status()
            out.append(resp.json()["embedding"])
    return out
