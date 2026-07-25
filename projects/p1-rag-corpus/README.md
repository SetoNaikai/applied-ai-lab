# P1 — RAG over a Real Document Corpus

**Phase 1 · Weeks 5–8 · ~40 hrs**

## Skills this closes
RAG pipelines · vector databases · embeddings · LLM provider APIs and frameworks

## Corpus
Maritime / cruise regulatory: public SEC filings (10-Ks of the major cruise operators),
CDC Vessel Sanitation Program manuals, public IMO/SOLAS documents. Target ≥500 documents,
mixed formats including scans.

Public sources only — see `AGENTS.md` (Security and data boundaries). Record source URI,
license, and retrieval date for every document; P7 depends on this being habitual.

## Deliverable checklist
- [ ] Ingestion pipeline with failure logging (`ingest_failures` table) and a parse-success rate by doc type
- [ ] Chunking experiment: ≥5 strategies × ≥3 embedding models, results in a committed table
- [ ] Hybrid retrieval (dense + lexical) with hand-written RRF
- [ ] Optional reranking, measured against no-rerank
- [ ] Grounded generation with inline citations
- [ ] Calibrated refusal when retrieval is weak
- [ ] **Framework-free reimplementation of the retrieval core** (raw SQL + embeddings API)
- [ ] Langfuse traces with cost per query
- [ ] ADR: vector store choice
- [ ] Write-up

## Run
```bash
python -m projects.p1_rag_corpus.main ingest --source data/corpus/
python -m projects.p1_rag_corpus.main index
python -m projects.p1_rag_corpus.main ask "What are the ballast water reporting requirements?"
pytest projects/p1-rag-corpus -m eval
```

## Findings
_Fill in as you go. This section is the raw material for the write-up — record surprises,
dead ends, and numbers while they are fresh._

### Chunking experiment results
| Strategy | Target tokens | Embedding model | recall@5 | mrr | faithfulness | cost/query |
|---|---|---|---|---|---|---|
| | | | | | | |

### What broke
-
