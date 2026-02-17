# PositionedUp

A personal branding and content automation platform. Go through a guided brand discovery chat, then generate YouTube content (scripts, hooks, thumbnails, titles) through an AI-powered pipeline. Built for creators who want to build a personal brand without hiring a team.

## What It Does

1. **Brand Discovery Chat** — An AI coach walks you through four modules (Foundation, ICA, Offer, Brand Statement) to define your brand positioning
2. **Content Pipeline** — An 8-node LangGraph pipeline researches trends, identifies gaps, generates scripts, creates hooks, and edits content
3. **Knowledge Base** — Upload PDFs, docs, links, and videos. The system extracts text, transcribes audio, and uses everything as context
4. **Performance Analytics** — Track content performance and let the AI learn what works for your audience
5. **Experiments** — A/B test hooks, titles, and thumbnails with built-in tracking

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 15, React 19, Tailwind CSS, TypeScript |
| Backend API | FastAPI, Python 3.9+ |
| Content Pipeline | LangGraph (8-node state machine) |
| Database | Supabase Postgres + pgvector + RLS |
| Auth | Supabase Auth (JWT) |
| LLM | OpenAI GPT-4o |
| Search | DuckDuckGo + Tavily (optional) |
| Transcription | YouTube captions + OpenAI Whisper fallback |
| OCR | GPT-4 Vision (scanned PDFs and images) |
| Queue | pgmq (Postgres message queue) |
| CI | GitHub Actions (lint + type check) |
| Testing | Pytest (611 tests) + Playwright E2E (52 tests) |

## Project Structure

```
apps/
  api/
    app/
      main.py              # FastAPI app entry point
      config.py            # Settings from .env via pydantic_settings
      auth.py              # Supabase JWT auth
      routers/             # 11 API routers
      schemas/             # Pydantic request/response models
      services/            # Business logic (chat, ingestion, research, etc.)
    worker/
      graph/
        pipeline.py        # LangGraph pipeline definition
        nodes/             # 8 pipeline nodes
        prompts/           # Prompt templates + writing style rules
      executor.py          # Pipeline runner
      queue.py             # pgmq integration
    tests/                 # 16 test files, 611 tests
  web/
    src/
      app/                 # Next.js pages (brand chat, content, schedule, etc.)
      components/          # Shared UI components
      lib/                 # API client, Supabase helpers
    tests/                 # 3 Playwright E2E test files, 52 tests
infra/
  supabase/migrations/     # 11 database migrations
docs/
  compound/                # Architecture docs, patterns, project log
```

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 20+
- pnpm
- A [Supabase](https://supabase.com) project
- An [OpenAI](https://platform.openai.com) API key

### 1. Clone and install

```bash
git clone https://github.com/nabilakhannn/PoistionedUp-App.git
cd PoistionedUp-App

# Backend
cd apps/api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../web
pnpm install
```

### 2. Configure environment

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

You will need to set:
- `SUPABASE_URL` and `SUPABASE_ANON_KEY` (from your Supabase dashboard)
- `SUPABASE_SERVICE_ROLE_KEY` (from Supabase Settings > API)
- `OPENAI_API_KEY` (from OpenAI platform)
- `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` (same as above, for the frontend)

### 3. Run database migrations

Apply the SQL migrations from `infra/supabase/migrations/` in order (001 through 011) against your Supabase project, either through the Supabase SQL editor or the CLI.

### 4. Start development servers

```bash
# Option A: Both at once
./dev.sh

# Option B: Separately
# Terminal 1 — Backend
cd apps/api && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd apps/web && pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Running Tests

```bash
# Backend unit tests (611 tests)
cd apps/api && python3 -m pytest tests/ -v

# Frontend E2E tests (52 tests)
cd apps/web && npx playwright test

# Lint
cd apps/api && ruff check .
cd apps/web && pnpm lint
```

## Content Pipeline

The 8-node LangGraph pipeline processes content through these stages:

```
signal_research → gap_analysis → topic_selection (pause for review)
→ hook_lab (pause for review) → script_generation → editor
→ testing → approval (pause for review)
```

Three interrupt points let you review and steer the pipeline before it continues.

## Chat Input Types

The brand chat accepts multiple input types alongside text:

| Input | Method |
|---|---|
| Text files (.txt, .md) | Direct read |
| CSV files | Row extraction |
| DOCX files | Paragraph extraction |
| PDFs (text-based) | pypdf extraction |
| PDFs (scanned/image) | GPT-4 Vision OCR |
| Images (.png, .jpg, etc.) | GPT-4 Vision text extraction |
| YouTube links | Captions, Whisper fallback |
| TikTok/Facebook videos | Whisper transcription via yt-dlp |
| Reddit posts | Post body + top comments |
| Twitter/X links | Tweet text + metrics |
| Substack articles | Full article text |
| Any website | trafilatura article extraction |

## License

Private project.
