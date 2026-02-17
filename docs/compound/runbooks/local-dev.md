# Local Development Runbook -- Content Orchestrator

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Node.js | 20.x LTS | `brew install node@20` or `nvm install 20` |
| pnpm | 9.x | `npm install -g pnpm` |
| Python | 3.11+ | `brew install python@3.11` or `pyenv install 3.11` |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker Desktop | latest | [docker.com](https://www.docker.com/products/docker-desktop) |
| Supabase CLI | 1.x | `brew install supabase/tap/supabase` |

---

## 1. Clone and Install Dependencies

```bash
git clone <repo-url> content-orchestrator
cd content-orchestrator

# Web app (Next.js)
cd apps/web && pnpm install && cd ../..

# API + Worker (FastAPI/Python)
cd apps/api && uv venv && source .venv/bin/activate && uv pip install -r requirements.txt && cd ../..
```

---

## 2. Start Supabase Locally

```bash
# First time only:
supabase init

# Every time:
supabase start
```

The output will show these values -- save them:
```
API URL:          http://127.0.0.1:54321
DB URL:           postgresql://postgres:postgres@127.0.0.1:54322/postgres
Studio URL:       http://127.0.0.1:54323
anon key:         eyJ...
service_role key: eyJ...
```

---

## 3. Run Migrations

```bash
supabase db reset
```

This runs all files in `infra/supabase/migrations/` in order. It creates:
- All 9 tables with RLS policies
- pgmq queues (workflow_jobs + dead-letter)
- Storage bucket (resource-uploads)
- Realtime publication on workflows table

---

## 4. Verify Schema

Open Supabase Studio at `http://127.0.0.1:54323` and check:
- **Table Editor tab:** all 9 tables exist (profiles, resources, resource_chunks, workflows, workflow_snapshots, content_assets, workflow_resources_used, audit_events, usage_costs)
- **Authentication > Policies:** RLS enabled on every table
- **Storage:** resource-uploads bucket exists

---

## 5. Environment Variables

```bash
cp .env.example .env
```

Then fill in the values from step 2. Your `.env` should look like:

```env
# === Supabase (local) ===
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=<anon key from supabase start>
SUPABASE_SERVICE_ROLE_KEY=<service_role key from supabase start>
SUPABASE_DB_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres

# === Next.js (web) ===
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key from supabase start>

# === FastAPI (api) ===
API_PORT=8000
CORS_ORIGINS=http://localhost:3000

# === LLM providers ===
OPENAI_API_KEY=sk-...

# === LangGraph checkpoint ===
LANGGRAPH_DB_URI=postgresql://postgres:postgres@127.0.0.1:54322/postgres

# === Agent Zero (optional, off by default) ===
AGENT_ZERO_ENABLED=false
AGENT_ZERO_DOCKER_IMAGE=agent0ai/agent-zero:latest
AGENT_ZERO_TIMEOUT_SECONDS=120

# === Cost governance ===
MAX_TOKENS_PER_STEP=32000
MAX_TOKENS_PER_WORKFLOW=200000
MAX_WORKFLOWS_PER_USER_PER_DAY=10

# === Observability ===
LOG_LEVEL=DEBUG
```

---

## 6. Start Services

You need 3 terminals (4 if using Agent Zero):

### Terminal 1 -- Next.js Dashboard
```bash
cd apps/web
pnpm dev
# Runs on http://localhost:3000
```

### Terminal 2 -- FastAPI Server
```bash
cd apps/api
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
# Runs on http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Terminal 3 -- Worker Process
```bash
cd apps/api
source .venv/bin/activate
python -m worker.main
# Long-running process, polls pgmq queue
```

### Terminal 4 (optional) -- Agent Zero
```bash
# Only if AGENT_ZERO_ENABLED=true
docker compose up agent-zero
```

---

## 7. Seed Test Data

```bash
cd apps/api
source .venv/bin/activate
python -m scripts.seed
```

This creates:
- 1 test user (test@example.com / password123)
- 1 profile with sample voice/audience settings
- 3 resources (1 link, 1 note, 1 transcript; 1 marked gold)
- Resource chunks for each resource
- 1 completed workflow with all content assets (for UI development)
- 1 queued workflow (for testing the worker)

**Manual alternative via Supabase Studio:**
1. Open `http://127.0.0.1:54323`
2. Go to Authentication > Users > Add user
3. Create `test@example.com` with password `password123`
4. Copy the user UUID
5. Go to Table Editor > profiles > Insert row with that UUID

---

## 8. Running Tests

```bash
# API tests
cd apps/api
pytest tests/ -v

# Web tests
cd apps/web
pnpm test

# RLS verification (critical -- run before every merge)
cd apps/api
pytest tests/test_rls.py -v
```

The RLS tests create two test users and verify that User A cannot access User B's data across all tables.

---

## 9. Day-to-Day Workflow

| What changed | What to do |
|-------------|-----------|
| Database schema | `supabase db reset` (re-runs all migrations) |
| API code | Auto-reloads (uvicorn --reload) |
| Web code | Auto-reloads (Next.js hot reload) |
| Worker code | Ctrl+C and restart `python -m worker.main` |
| Dependencies (Python) | `uv pip install -r requirements.txt` |
| Dependencies (Node) | `pnpm install` in `apps/web/` |

---

## 10. Stopping Everything

```bash
# Stop Supabase (preserves data)
supabase stop

# Stop Supabase and wipe all data
supabase stop --no-backup
```

Ctrl+C stops the other terminals.

---

## 11. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `supabase start` hangs | Make sure Docker Desktop is running. `docker ps` should work. |
| Migration fails on `pgmq.create` | Upgrade Supabase CLI: `brew upgrade supabase` |
| Worker not picking up jobs | Check `SUPABASE_SERVICE_ROLE_KEY` is correct. Try `SELECT * FROM pgmq.read('workflow_jobs', 0, 1);` in Studio SQL editor. |
| Realtime not firing | Verify `ALTER PUBLICATION supabase_realtime ADD TABLE workflows;` ran. Check Studio > Realtime > Inspector. |
| LangGraph checkpoint error | Use direct DB connection (port 54322), not the API (54321). Run `checkpointer.setup()` once. |
| `auth.uid()` is null in RLS | Make sure you're passing the JWT in the Authorization header. The anon key alone won't work for authenticated queries. |
| Storage upload 403 | Check that the file path starts with `{user_id}/`. Storage RLS requires `(storage.foldername(name))[1] = auth.uid()::text`. |
