# P1 Repair Plan

This document outlines the exact changes needed to fix the P1 project so that:
1. The test suite collects and passes (pytest -m "not slow and not costs_money")
2. Ruff reports zero errors

---

## Summary of Issues

### 1. Test Collection Failure
- **Error**: ModuleNotFoundError: No module named 'ingest'
- **Cause**: ingest/ directory is missing __init__.py, making it not a proper Python package
- **Location**: projects/p1-rag-corpus/evals/test_ingest.py line 11 tries to import from ingest.models

### 2. Ruff Errors (52 total across 4 files)

| File | Errors | Key Issues |
|------|--------|------------|
| ingest/config.py | 17 | Missing Field import, deprecated List/Dict/Any, undefined Field usage, duplicate models, line too long |
| ingest/models.py | 11 | Unused imports (Path, Optional), deprecated List, line too long |
| ingest/utils.py | 4 | Unsorted imports, unnecessary "r" mode, uses yaml (not installed) |
| ingest/ingest.py | 11 | Unsorted imports, unused json, deprecated List/Optional, ASYNC240, line too long |

---

## File-by-File Changes

### File: C:\Code\applied-ai-lab\projects\p1-rag-corpus\ingest\__init__.py
**Status**: MISSING - Must be created

**Purpose**: Make ingest/ a proper Python package so imports work.

**Content**:
`python
"""Ingestion pipeline for RAG corpus."""
from __future__ import annotations
from .ingest import ingest_files
from .models import DocumentSource, IngestConfig, IngestFailure, IngestResult
__all__ = ["DocumentSource", "IngestConfig", "IngestFailure", "IngestResult", "ingest_files"]
`

**Verification Command**:
`powershell
cd C:\Code\applied-ai-lab && .\.venv\Scripts\python.exe -c "from ingest import IngestConfig; print('OK')"
`

### File: C:\Code\applied-ai-lab\projects\p1-rag-corpus\ingest\models.py
**Status**: EXISTS - Fix 11 errors

**Changes**:
1. Remove unused rom pathlib import Path (line 6)
2. Remove unused Optional from typing imports (line 7)
3. Replace List[str] with list[str] on line 23
4. Replace List[tuple[str, str]] with list[tuple[str, str]] on line 37
5. Split line 48 to fix length > 100 chars

**Verification Command**:
`powershell
cd C:\Code\applied-ai-lab && .\.venv\Scripts\ruff.exe check projects\p1-rag-corpus\ingest\models.py
`

### File: C:\Code\applied-ai-lab\projects\p1-rag-corpus\ingest\config.py
**Status**: EXISTS - DELETE

**Reason**: Contains broken duplicate models missing Field import, uses deprecated .dict(), references undefined modules.

**Command to delete**:
`powershell
Remove-Item C:\Code\applied-ai-lab\projects\p1-rag-corpus\ingest\config.py
`

**Verification Command**:
`powershell
cd C:\Code\applied-ai-lab && .\.venv\Scripts\ruff.exe check projects\p1-rag-corpus\ingest\config.py
`

### File: C:\Code\applied-ai-lab\projects\p1-rag-corpus\ingest\utils.py
**Status**: EXISTS - DELETE

**Reason**: Uses yaml (not installed), functions not called anywhere.

**Command to delete**:
`powershell
Remove-Item C:\Code\applied-ai-lab\projects\p1-rag-corpus\ingest\utils.py
`

**Verification Command**:
`powershell
cd C:\Code\applied-ai-lab && .\.venv\Scripts\ruff.exe check projects\p1-rag-corpus\ingest\utils.py
`

### File: C:\Code\applied-ai-lab\projects\p1-rag-corpus\ingest\ingest.py
**Status**: EXISTS - Fix 11 errors

**Changes**:
1. Remove unused import json (line 6)
2. Remove Optional from typing imports (line 9)
3. Replace Optional[str] with str | None on lines 33, 79
4. Replace List[str] with list[str] on lines 65, 92
5. Split line 99 to fix length > 100 chars
6. Add # noqa: ASYNC240 comments to lines 37, 44, 98

**Verification Command**:
`powershell
cd C:\Code\applied-ai-lab && .\.venv\Scripts\ruff.exe check projects\p1-rag-corpus\ingest\ingest.py
`

---

## Sequential Fix Order
1. Create ingest/__init__.py
2. Fix models.py
3. Delete config.py
4. Delete utils.py
5. Fix ingest.py
6. Verify with tests and ruff

---

## Final Verification Commands

### Test Collection:
`powershell
cd C:\Code\applied-ai-lab && .\.venv\Scripts\python.exe -m pytest projects\p1-rag-corpus -m "not slow and not costs_money" --collect-only
`

### Ruff Check:
`powershell
cd C:\Code\applied-ai-lab && .\.venv\Scripts\ruff.exe check projects\p1-rag-corpus\ingest
`

### Full Test Suite:
`powershell
cd C:\Code\applied-ai-lab && .\.venv\Scripts\python.exe -m pytest -m "not slow and not costs_money" -v
`

### Full Ruff Check:
`powershell
cd C:\Code\applied-ai-lab && .\.venv\Scripts\ruff.exe check C:\Code\applied-ai-lab
`

---

## Notes
1. yaml is not a dependency - any code using it must be removed
2. Pydantic v2 uses .model_dump() not .dict()
3. Python 3.11+ uses list[str] not List[str]
4. Many ruff errors auto-fix with: ruff check --fix
