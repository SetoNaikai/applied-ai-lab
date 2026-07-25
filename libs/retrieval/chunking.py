"""Chunking strategies.

This is a data modelling problem wearing a new hat -- which is why fifteen
years of warehouse design transfers directly. Run the grid, measure with
libs.evals, and let the numbers pick the strategy. Do not guess.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class ChunkStrategy(StrEnum):
    FIXED = "fixed"
    RECURSIVE = "recursive"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"


@dataclass
class Chunk:
    content: str
    index: int
    token_count: int
    metadata: dict[str, object]


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    try:
        import tiktoken

        return len(tiktoken.get_encoding(model).encode(text))
    except Exception:  # noqa: BLE001 - fall back to a rough heuristic
        return max(1, len(text) // 4)


def chunk_document(
    text: str,
    *,
    strategy: ChunkStrategy = ChunkStrategy.RECURSIVE,
    target_tokens: int = 512,
    overlap_tokens: int = 50,
    metadata: dict[str, object] | None = None,
) -> list[Chunk]:
    metadata = dict(metadata or {})
    metadata["chunk_strategy"] = str(strategy)
    metadata["target_tokens"] = target_tokens

    if strategy is ChunkStrategy.PARAGRAPH:
        pieces = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    elif strategy is ChunkStrategy.SENTENCE:
        pieces = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    elif strategy is ChunkStrategy.RECURSIVE:
        pieces = _recursive_split(text, target_tokens)
    else:
        pieces = _fixed_split(text, target_tokens, overlap_tokens)

    return [
        Chunk(content=p, index=i, token_count=count_tokens(p), metadata=dict(metadata))
        for i, p in enumerate(_merge_to_target(pieces, target_tokens))
    ]


def _fixed_split(text: str, target: int, overlap: int) -> list[str]:
    words = text.split()
    per_chunk = max(1, int(target * 0.75))  # ~0.75 words per token
    step = max(1, per_chunk - int(overlap * 0.75))
    return [" ".join(words[i : i + per_chunk]) for i in range(0, len(words), step)]


def _recursive_split(text: str, target: int) -> list[str]:
    """Split on the largest natural boundary that fits, then descend."""
    for separator in ("\n## ", "\n\n", "\n", ". "):
        if separator in text:
            parts = [p for p in text.split(separator) if p.strip()]
            out: list[str] = []
            for part in parts:
                if count_tokens(part) > target * 2:
                    out.extend(_recursive_split(part, target))
                else:
                    out.append(part.strip())
            return out
    return [text.strip()]


def _merge_to_target(pieces: list[str], target: int) -> list[str]:
    """Combine small fragments so chunks land near the target size."""
    merged: list[str] = []
    buffer: list[str] = []
    buffered_tokens = 0
    for piece in pieces:
        tokens = count_tokens(piece)
        if buffered_tokens + tokens > target and buffer:
            merged.append("\n\n".join(buffer))
            buffer, buffered_tokens = [], 0
        buffer.append(piece)
        buffered_tokens += tokens
    if buffer:
        merged.append("\n\n".join(buffer))
    return merged
