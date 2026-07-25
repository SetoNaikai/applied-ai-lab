"""Verify the lab: local inference, frontier inference, embeddings, Postgres.

Run after `make up`. If all four pass, the lab exists.
"""

from __future__ import annotations

import asyncio

from rich.console import Console
from rich.table import Table

from libs.llm import LLM, Budget, embed
from libs.settings import get_settings

console = Console()
PROMPT = "In two sentences, explain what a vector embedding is."


async def check_local() -> tuple[bool, str]:
    settings = get_settings()
    try:
        out = await LLM(model=settings.local_model).complete(PROMPT)
        return True, f"{out.latency_s:.1f}s, {out.output_tokens} tok"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


async def check_frontier() -> tuple[bool, str]:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return False, "ANTHROPIC_API_KEY not set in .env"
    try:
        budget = Budget(limit_usd=0.10)
        out = await LLM(budget=budget).complete(PROMPT)
        return True, f"{out.latency_s:.1f}s, ${out.cost_usd:.5f}"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


async def check_embeddings() -> tuple[bool, str]:
    settings = get_settings()
    try:
        vectors = await embed(["hello", "안녕하세요"])
        dim = len(vectors[0])
        if dim != settings.embedding_dim:
            return False, (
                f"dim {dim} != EMBEDDING_DIM {settings.embedding_dim} "
                "-- update .env and the vector(n) column"
            )
        return True, f"dim {dim}, multilingual ok"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def check_postgres() -> tuple[bool, str]:
    try:
        import psycopg

        with psycopg.connect(get_settings().database_url) as conn, conn.cursor() as cur:
            cur.execute("SELECT extname FROM pg_extension WHERE extname IN ('vector','pg_trgm')")
            found = {r[0] for r in cur.fetchall()}
        missing = {"vector", "pg_trgm"} - found
        if missing:
            return False, f"missing extensions: {', '.join(sorted(missing))}"
        return True, "pgvector + pg_trgm present"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


async def main() -> int:
    local, frontier, embeddings = await asyncio.gather(
        check_local(), check_frontier(), check_embeddings()
    )
    postgres = check_postgres()

    table = Table(title="Applied AI Lab -- smoke test")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail", overflow="fold")

    results = [
        ("Local inference (Ollama)", local),
        ("Frontier inference (Anthropic)", frontier),
        ("Embeddings", embeddings),
        ("Postgres / pgvector", postgres),
    ]
    for name, (ok, detail) in results:
        table.add_row(name, "[green]PASS[/]" if ok else "[red]FAIL[/]", detail)

    console.print(table)
    failed = [name for name, (ok, _) in results if not ok]
    if failed:
        console.print(f"\n[red]{len(failed)} check(s) failed:[/] {', '.join(failed)}")
        console.print("Try: [bold]make up[/] then [bold]make models[/], and check .env")
        return 1
    console.print("\n[green]Lab is up.[/] Commit this and start P1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
