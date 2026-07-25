# Getting Started

## 1. Open it

```bash
git clone <this-repo> && cd applied-ai-lab
code .
```

Read `AGENTS.md` first — it is the working contract for humans and any coding agent
(local LLM clients, Claude Code, whatever you drive the repo with).

## 2. Make it run

```bash
cp .env.example .env      # add API keys; set LOCAL_LLM_BASE_URL if you run a local gateway
make install
make up                   # docker: ollama, postgres/pgvector, qdrant
make models               # ~10 min, pulls local models (skip if using your own gateway)
make smoke                # all checks should pass
make test                 # unit tests, no network needed
```

If `make smoke` fails on embeddings with a dimension mismatch, the model you pulled has a
different dimension than `EMBEDDING_DIM` in `.env` — fix the env var *and* the
`vector(1024)` column in `sql/init/01-schema.sql`, then recreate the volume.

Already running local inference (LiteLLM, Ollama, vLLM)? Set `LOCAL_LLM_BASE_URL` in
`.env` and skip the `ollama` compose service entirely.

## 3. The weekly ritual

```powershell
pwsh scripts/new-week.ps1     # stamps docs/tracker/<year>-W<nn>.md from the template
```

Fill it in by hand at week's end — hours, what shipped, what broke, next week's one
thing. Four minutes. `docs/ROADMAP.md` holds the phase plan and current status; keep its
Status section current.

## What's deliberately not here

- **P1–P7 implementations.** Scaffolds and eval harnesses only — building them is the
  point. Each project's `README.md` is its spec.
- **Corpus data.** `data/` is gitignored. Public sources only; see `AGENTS.md`
  (Security and data boundaries).
- **Langfuse in compose.** Commented out — v3 self-hosting added ClickHouse, Redis, and
  S3-compatible storage. Check their current self-hosting docs before uncommenting.

## Worth knowing

- Losing the `pgdata` volume after building a large corpus is a genuinely bad afternoon —
  never run `docker compose down -v` casually, and back the volume up once corpora exist.
- Every project ships with evals; `make eval-fast` is the PR gate. Don't loosen a CI
  threshold to make a build pass (see `AGENTS.md`).
