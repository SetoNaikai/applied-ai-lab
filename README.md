# Applied AI Lab

Applied AI engineering portfolio: RAG, evaluation harnesses, agentic systems,
fine-tuning economics, and an enterprise document-intelligence platform.

## Quick start

```bash
git clone <this-repo> && cd applied-ai-lab
cp .env.example .env          # add your API keys
make install                  # python deps
make up                       # docker: ollama, postgres/pgvector, qdrant, langfuse
make models                   # pull local models (~10 min)
make smoke                    # verify local + frontier inference
make test
```

Open <http://localhost:3000> for Open WebUI, <http://localhost:3001> for Langfuse.

## Projects

| # | Project | Phase | Focus |
|---|---|---|---|
| P1 | [RAG over a document corpus](projects/p1-rag-corpus/) | 1 | Chunking, embeddings, hybrid retrieval, grounded citations |
| P2 | [Evaluation harness](projects/p2-eval-harness/) | 1 | Golden datasets, LLM judge, hallucination detection, CI gating |
| P3 | [Agentic ops copilot](projects/p3-agentic-copilot/) | 2 | LangGraph, tool calling, MCP, multi-agent, reliability |
| P4 | [Fine-tuning & serving](projects/p4-finetune/) | 3 | LoRA, quantization, vLLM, build-vs-buy cost model |
| P5 | [Full-stack AI app](projects/p5-fullstack/) | 4 | Next.js + TypeScript, text-to-SQL, streaming |
| P6 | [Korean tutor](projects/p6-korean-tutor/) | 4 | FSRS scheduling, rubric grading, Whisper pronunciation |
| P7 | [Document intelligence platform](projects/p7-capstone/) | 5 | Capstone: ingestion at scale, governance, extraction |

## Documentation

- [Roadmap and current status](docs/ROADMAP.md)
- [Architecture decision records](docs/adr/)
- [Write-ups](docs/writeups/)
- [Working rules](AGENTS.md)

## Local models

`libs/llm` speaks to Anthropic, OpenAI, or any OpenAI-compatible local gateway
(set `LOCAL_LLM_BASE_URL` in `.env` — LiteLLM, Ollama, vLLM all work). The compose file
ships a self-contained stack for clean machines; if you already run local inference,
point the env var at it and skip those services.
