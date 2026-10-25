# SmartStudy API (FastAPI)

Python backend for boards, autosave, and assistant chat. Auth is **Clerk JWT** (`Authorization: Bearer <token>` from the Next.js app).

Database: **SQLAlchemy** (async) + **Alembic** migrations.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: DATABASE_URL must use postgresql+asyncpg://...
```

Start Postgres (from repo root): `docker compose up -d postgres`

### Migrations (Alembic)

**Fresh database:**

```bash
.venv/bin/alembic upgrade head
# or from repo root: npm run db:migrate
```

**Already migrated with Prisma** (tables exist): stamp Alembic without re-running DDL:

```bash
.venv/bin/alembic stamp head
# or: npm run db:stamp
```

Create a new revision after model changes:

```bash
.venv/bin/alembic revision --autogenerate -m "describe change"
.venv/bin/alembic upgrade head
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

Or from repo root: `npm run dev:api`

Health check: http://127.0.0.1:8000/health

## AI agent prompts

Edit system prompts in **`backend/app/prompts.py`**:

- `ROUTER_AGENT_PROMPT` — needs board? message type
- `VISION_AGENT_PROMPT` — screenshot → JSON
- `TUTOR_AGENT_PROMPT` — JSON + question → `{ message, todraw }`
- `DRAW_AGENT_PROMPT` — `todraw` → Excalidraw elements (`POST /boards/{id}/assistant/draw`)

- `CONTEXT_FILTER_AGENT_PROMPT` — prunes board JSON to elements relevant to the question (runs between vision and tutor)

Secrets (`GEMINI_API_KEY`, DB URL) stay in `backend/.env`.

Gemini is called through the **`google-genai`** SDK (native async client). Transient HTTP 503 errors are retried with exponential backoff (`GEMINI_MAX_ATTEMPTS`); 429 fails fast.

## Autosave, versions and retention

- `PUT /boards/{id}/snapshot` appends a new `BoardSnapshot` row; `UNIQUE (boardId, version)` guards against concurrent writers (the loser retries with the next version).
- A stale `baseVersion` still saves but returns `staleWarning: true`.
- Only the newest `SNAPSHOT_RETENTION` (default 50) versions per board are kept.

## Maintenance

Soft-deleted boards are permanently removed after the 30-day restore window:

```bash
python -m app.cli purge-boards
```

Run it periodically, e.g. cron: `0 3 * * * cd /path/to/backend && .venv/bin/python -m app.cli purge-boards`.

## Rate limiting

All `/boards/{id}/assistant/*` endpoints are limited per user (`AI_RATE_LIMIT_PER_MINUTE`, default 20, HTTP 429 `RATE_LIMITED`). The limiter is in-memory (per process); use a shared store such as Redis with multiple workers.

## Clerk

1. Create an application at https://dashboard.clerk.com
2. Set **JWKS URL** in `backend/.env` as `CLERK_JWKS_URL` (Clerk Dashboard → API Keys → Advanced → JWKS Endpoint)
3. In `frontend/.env`: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`
4. Optional hardening: set `CLERK_ISSUER` (your Clerk Frontend API URL) so tokens from other issuers are rejected.
