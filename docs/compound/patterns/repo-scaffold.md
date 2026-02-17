# Pattern: Repo Scaffold

## What this is
The monorepo structure for Content Orchestrator.

## Structure
```
content-orchestrator/
  apps/
    web/               # Next.js 15 + Tailwind + TypeScript
    api/               # FastAPI + Python 3.11
      app/             # API routes, schemas, services
      worker/          # Background worker + LangGraph pipeline
      tests/           # API + RLS tests
      scripts/         # Seed data, migrations
  packages/
    shared/schemas/    # JSON schemas shared between frontend and backend
  infra/
    supabase/migrations/  # SQL migrations
  docs/
    compound/          # Architecture, decisions, patterns, runbooks
  .github/workflows/   # CI pipeline
  .env.example         # All env vars with placeholders
  .gitignore           # Secrets excluded
```

## Key decisions
- **pnpm** for Node dependencies (web)
- **uv/pip** for Python dependencies (api)
- **Separate venv** per Python service (`apps/api/.venv/`)
- **Tailwind CSS v3** with autoprefixer for styling
- **FastAPI config via pydantic-settings** (reads from .env automatically)

## Gotchas
- Next.js 15 requires `autoprefixer` as explicit devDependency
- pnpm must be installed globally before `pnpm install` works
- Python venv must be activated before running API/worker
