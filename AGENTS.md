# AGENTS.md — how to work in this repo

Universal entry point for **any** coding agent or human working here (local LLM clients,
Claude Code, or you). Read this, then `docs/ROADMAP.md` for the current phase.

## What this repo is

Applied AI engineering portfolio and learning monorepo: seven projects
(`projects/p1`–`p7`) sharing one internal library (`libs/`). The shared library is the
point — it makes the repo read as a platform, not seven tutorials. **Anything built in a
project that could be reused belongs in `libs/`.**

| Path | Contents |
|---|---|
| `libs/llm/` | Provider abstraction (Anthropic / OpenAI / local OpenAI-compatible gateway). All model calls go through here. |
| `libs/retrieval/` | Chunking, embedding, pgvector store, hybrid search |
| `libs/evals/` | Golden datasets, metrics, LLM judge, runner. **Imported by every project.** |
| `libs/obs/` | Langfuse tracing wrappers |
| `projects/pN-*/` | One directory per project: `main.py` + `README.md` + `evals/` |
| `docs/ROADMAP.md` | Phases, milestones, current status |
| `docs/tracker/` | Weekly progress logs (`scripts/new-week.ps1` stamps a new one) |
| `docs/adr/` | Architecture decision records — one per significant choice |
| `docs/writeups/` | One article per completed project |
| `sql/init/` | Postgres schema, applied on container first boot |

## Commands

- Install: `make install` (uses `uv`; falls back to pip)
- Lab up / down: `make up` / `make down` · Smoke: `make smoke`
- Tests: `make test` (fast subset: `make test-fast`)
- Lint + format + typecheck: `make check`
- Evals: `make eval-fast` (PR gate) · `make eval` (full)

## Model access

All LLM calls go through `libs/llm`. Never call a provider SDK directly from a project.
Providers: `anthropic`, `openai`, and `local` — any OpenAI-compatible gateway
(`LOCAL_LLM_BASE_URL` in `.env`, e.g. a LiteLLM/Ollama endpoint). When using a local
gateway, reference **role aliases** (e.g. `coding-agent`, `fast-agent`), never a specific
model tag — the model behind an alias is swappable and tags go stale.

## Python conventions

- Python 3.11+, modern syntax (`X | None`, `list[str]`, `StrEnum`); `from __future__
  import annotations` in every module.
- **Full type hints everywhere** — `mypy libs` passes with `disallow_untyped_defs`.
- **Async by default** for anything touching a network; never a blocking HTTP client
  inside an async function.
- **`pydantic` models for all structured data** crossing a boundary. No bare dicts as
  informal schemas.
- `ruff`, line length 100. Run `make check` before declaring work done.
- Errors: catch narrowly. The one sanctioned broad catch is in an eval runner, where a
  crash is itself a result to record.
- No `print` in `libs/` (logging there; `rich` in scripts).
- `pytest` with `asyncio_mode = "auto"`. New behavior needs a test in the same commit.
  Paid-API tests marked `@pytest.mark.costs_money`, slow ones `@pytest.mark.slow`.
  Deterministic logic (chunking, RRF, metrics) is tested without any network call.

## Evaluation rules (blast radius: everything)

- **Never mutate a metric definition in place** — version it. Historical `eval_runs`
  rows must stay comparable.
- **Golden dataset cases are written from source documents, never from retrieved
  chunks.** ~20% of cases must be unanswerable (correct behavior is refusal).
- **Validate the judge**: any new rubric needs measured human agreement on ~30 cases
  (recorded in the project README; below 0.80, tighten the rubric first).
- Judge parse failures resolve to `fail`, never `pass`.
- Every eval run passes a `Budget`. No unbounded loops over paid API calls.
- Never loosen a CI threshold to make a build pass — fix the regression or ADR why the
  threshold was wrong.

## Security and data boundaries (absolute)

- **No employer or workplace data in this repository, ever** — no exports, schemas,
  ticket text, screenshots, or "anonymized" samples. Public sources only: SEC filings,
  government publications, public standards, openly licensed or synthetic data. Record
  provenance (source URI, license, retrieval date) for every corpus.
- **No secrets in git.** Keys live in `.env` (gitignored); `.env.example` carries empty
  values only. Never read or echo `.env`.
- Generated SQL (P5/P7): read-only role, parse-validated single `SELECT`, `LIMIT` +
  statement timeout, SQL always shown to the user.
- Any script looping over LLM calls uses a `Budget` with a hard ceiling.

## Working rules

- Small commits with real messages — this history is a portfolio artifact.
- Significant choices get an ADR (`docs/adr/`), not a buried comment.
- Every project ships with evals in `projects/pN-*/evals/`. A project without evals is
  unfinished.
- Risk zones (plan before editing): `sql/init/` (fresh-volume only — schema changes need
  a migration note), `libs/evals/` (version, don't mutate), `.github/workflows/ci.yml`
  (the eval gate), embedding dimensions (must match the `vector(n)` column — a new model
  means a new collection).
- Stop and ask before: adding a heavy dependency, starting a project out of phase order,
  or exceeding a project's stated scope.
