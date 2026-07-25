"""Langfuse tracing wrappers.

Degrades to a no-op when Langfuse is not configured, so nothing here can break
a local run. Observability is an explicit JD requirement -- wire it early, not
after the fact.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any, TypeVar

from libs.settings import get_settings

F = TypeVar("F", bound=Callable[..., Any])


def _client() -> Any | None:
    settings = get_settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None
    try:
        from langfuse import Langfuse

        return Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except ImportError:
        return None


@contextmanager
def trace(name: str, **metadata: Any):
    """Context manager for a named span."""
    client = _client()
    if client is None:
        yield None
        return
    span = client.trace(name=name, metadata=metadata)
    try:
        yield span
    finally:
        client.flush()


def traced(name: str | None = None) -> Callable[[F], F]:
    """Decorator that traces an async function call."""

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            with trace(name or fn.__qualname__):
                return await fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
