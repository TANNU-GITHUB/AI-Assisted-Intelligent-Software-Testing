# Architecture documentation

This repository's detailed system and workflow documentation is maintained in [README.md](../README.md).

The Mermaid source for the system diagram is in [system-architecture.mmd](./system-architecture.mmd).

## Runtime topology

- Browser: Next.js pages and the React Live Lab.
- Frontend: Next.js on port 3000.
- Backend: FastAPI/Uvicorn on port 8000.
- Identity data: SQLite in `backend/data/auth.db`.
- Analysis data: JSON and generated files in `backend/sessions/<session_id>/`.
- Optional providers: NVIDIA NIM and local Ollama.

## Request flow

```text
Browser
  -> Next.js middleware (route protection)
  -> /api/* Next.js rewrite
  -> FastAPI route
  -> ownership/auth validation
  -> session or provider/analysis module
  -> session.json and generated files
  -> JSON, HTML report, or dashboard data
```

## Main workflow

```text
Authenticate
  -> Create session
  -> Extract requirements, if needed
  -> Analyze source code
  -> Analyze/structure requirements
  -> Generate white/black/gray/other tests
  -> Execute pytest
  -> Measure branch coverage
  -> Fill uncovered lines/requirements
  -> Re-execute and re-measure
  -> Render downloadable HTML report
```
