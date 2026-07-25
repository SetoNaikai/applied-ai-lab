# Roadmap — Aug 2026 → Jul 2027

Seven projects across six phases, each building on the last, all sharing `libs/`.
Detailed per-project specs live in each project's own `README.md`.

| Phase | Weeks | Theme | Ships |
|---|---|---|---|
| 0 | Aug 2026 | Foundations: tooling, Python fluency, repo + CI live | Working smoke test, CI green |
| 1 | Sep – Oct 2026 | RAG + evaluation — the core competency | **P1** RAG pipeline, **P2** eval harness |
| 2 | Nov – Dec 2026 | Agentic systems + orchestration | **P3** agentic triage copilot |
| 3 | Jan – Feb 2027 | Fine-tuning, serving, MLOps | **P4** LoRA + serving + cost model |
| 4 | Feb – Apr 2027 | Full-stack AI apps | **P5** Next.js analytics copilot, **P6** Korean tutor |
| 5 | Apr – Jun 2027 | Capstone | **P7** document-intelligence platform |
| 6 | Jun – Jul 2027 | Consolidate + publish | Write-ups, portfolio site |

## Standing rules for the year

1. **Public commits over private perfection.**
2. **Every project ends in a write-up** (`docs/writeups/`).
3. **Evals on everything** — a RAG pipeline without an eval suite is a demo, not a system.
4. **One course active at a time.** Courses serve projects, never the reverse.
5. Projects run in phase order; each imports what the previous one built.

## Status

- **Current phase:** 0 (foundations)
- **In flight:** repo scaffold, CI, `libs/llm` provider abstraction
- Weekly progress: `docs/tracker/`
