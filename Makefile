.PHONY: help install up down logs models smoke test test-fast check fmt eval eval-fast psql clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:  ## Install python deps (uv preferred)
	@command -v uv >/dev/null 2>&1 && uv pip install -e ".[retrieval,evals,agents,obs,dev]" \
		|| pip install -e ".[retrieval,evals,agents,obs,dev]"

up:  ## Start the lab containers
	docker compose up -d
	@echo "Open WebUI  -> http://localhost:3000"
	@echo "Langfuse    -> http://localhost:3001"

down:  ## Stop containers (volumes preserved)
	docker compose down

logs:  ## Tail container logs
	docker compose logs -f --tail=50

models:  ## Pull local models
	docker exec -it ollama ollama pull llama3.1:8b
	docker exec -it ollama ollama pull qwen2.5:7b
	docker exec -it ollama ollama pull qwen2.5-coder:7b
	docker exec -it ollama ollama pull bge-m3

smoke:  ## Verify local + frontier inference
	python scripts/smoke_test.py

test:  ## Full test suite
	pytest -v

test-fast:  ## Skip slow / paid tests
	pytest -v -m "not slow and not costs_money"

check:  ## Lint, format, typecheck
	ruff check --fix .
	ruff format .
	mypy libs

fmt:  ## Format only
	ruff format .

eval:  ## Full eval regression suite
	pytest -v -m eval

eval-fast:  ## Fast eval subset (CI on every PR)
	pytest -v -m "eval and not slow"

psql:  ## Postgres shell
	docker exec -it pgvector psql -U lab -d lab

clean:  ## Remove caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache
