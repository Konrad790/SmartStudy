# SmartStudy

[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2015-black?style=flat&logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2016-336791?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![TypeScript](https://img.shields.io/badge/Language-TypeScript-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Language-Python%203.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-4285F4?style=flat&logo=googlegemini&logoColor=white)](https://ai.google.dev/)

**SmartStudy** is an AI-powered study whiteboard. Students solve problems on an infinite
[Excalidraw](https://excalidraw.com/) canvas while an AI tutor *looks at the board*, understands
the handwritten/drawn content, answers questions in context, and can propose drawings
(diagrams, steps, corrections) straight onto the canvas.

> **Project status:** working prototype / MVP. The AI pipeline is intentionally modular so that its
> weakest parts can be replaced one at a time (see [Roadmap](#roadmap--known-limitations)).

<p align="center">
  <img src="readme_files/demo.gif" alt="SmartStudy demo: drawing on the whiteboard and asking the AI tutor" width="900">
</p>

---

## Table of Contents

- [Screenshots](#screenshots)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [AI Pipeline (multi-agent)](#ai-pipeline-multi-agent)
- [Database Architecture](#database-architecture)
- [API Reference](#api-reference)
- [Frontend Architecture](#frontend-architecture)
- [Engineering Highlights](#engineering-highlights)
- [Roadmap & Known Limitations](#roadmap--known-limitations)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Testing](#testing)
- [Repository Structure](#repository-structure)

---

## Screenshots

| Landing page | Boards workspace |
|---|---|
| ![Landing page](readme_files/landing.png) | ![Boards list](readme_files/boards.png) |

---

## Key Features

| Feature | Description |
|---|---|
| **Infinite whiteboard** | Excalidraw canvas with a custom theme, per-user boards, soft-delete and restore. |
| **Autosave with versioning** | Debounced autosave (800 ms), flush on tab hide / page leave, versioned snapshots in PostgreSQL. |
| **Optimistic concurrency** | Concurrent writers (e.g. two tabs) are detected; the client is warned about a stale state. |
| **AI tutor with vision** | The tutor sees the board (screenshots are converted into structured JSON) and answers with conversation history and viewport awareness. |
| **Streaming answers** | Tutor replies stream token-by-token over Server-Sent Events with live pipeline status ("Analyzing question…", "Inspecting whiteboard…"). |
| **Math rendering** | Markdown + LaTeX (KaTeX) in the chat, with a streaming parser that preserves LaTeX backslashes. |
| **Draw proposals** | The tutor can emit a structured `todraw` plan; a dedicated Draw agent converts it into Excalidraw elements the student previews and accepts/rejects. |
| **Background vision sync** | After the student stops drawing, only the *changed* region is re-analysed and merged into the board's stored context. |
| **Conversation history** | Multiple chat threads per board, listed in the sidebar, resumable and deletable. |
| **Auth** | Clerk authentication; the backend verifies JWTs against Clerk's JWKS and checks the issuer. |
| **Rate limiting & resilience** | Per-user AI rate limit, retry with exponential backoff on transient Gemini 503s, graceful fallbacks on malformed model output. |

---

## Tech Stack

**Frontend** — Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, `@excalidraw/excalidraw`,
TanStack Query, Clerk, Zod, `react-markdown` + `remark-math` + `rehype-katex`, Vitest, Playwright.

**Backend** — FastAPI, SQLAlchemy 2 (async) + asyncpg, Alembic, Pydantic v2 / pydantic-settings,
PyJWT, `google-genai` SDK, pytest.

**Infrastructure** — PostgreSQL 16 (Docker Compose), Clerk (auth), Google Gemini / Gemma (AI).

---

## System Architecture

```mermaid
flowchart LR
    subgraph Browser["Browser (Next.js 15)"]
        EX[Excalidraw canvas]
        AS[Autosave hook]
        VS[Vision-sync hook]
        CH[Assistant sidebar<br/>chat + SSE]
    end

    subgraph API["FastAPI backend"]
        AU[Clerk JWT auth<br/>+ rate limit]
        BR[Boards router]
        SR[Snapshots router]
        AR[Assistant router]
        PL[AI pipeline<br/>services/gemini.py]
    end

    DB[(PostgreSQL 16)]
    CLERK[Clerk JWKS]
    GEM[Google Gemini API]

    EX --> AS -->|PUT snapshot| SR
    EX --> VS -->|POST vision-sync| AR
    CH -->|POST chat/stream| AR
    AU -.verifies.-> CLERK
    BR & SR & AR --> DB
    AR --> PL --> GEM
```

**Request flow for a chat message**

1. The user sends a message. The frontend prepares board context: if elements changed since the
   last analysis it exports a **screenshot of only the changed region** (a *patch*) plus the
   current viewport; otherwise it sends no image at all.
2. `POST /boards/{id}/assistant/chat/stream` runs the AI pipeline and streams SSE events
   (`status` → `delta`… → `done`).
3. The user message, the tutor reply and (if updated) the board context are persisted.

---

## AI Pipeline (multi-agent)

The tutor is not one prompt but a small pipeline of specialised agents, each with its own model
setting so that cheap/fast models handle cheap/fast tasks.

```mermaid
flowchart TD
    U[Student message + history] --> R{Router agent}
    R -->|needs_board = false| T
    R -->|needs_board = true| V{Screenshot<br/>available?}
    V -->|patch + existing context| VP[Vision Patch agent<br/>analyse crop, merge into context]
    V -->|full image| VF[Vision Parser agent<br/>full board → JSON]
    V -->|no image| C[Reuse stored board context]
    VP --> F
    VF --> F
    C --> F
    F[Context Filter agent<br/>prune to relevant elements] --> T[Tutor agent<br/>streamed answer + optional todraw]
    T -->|todraw plan| D[Draw agent<br/>→ Excalidraw elements]
    T --> OUT[Reply to student]
```

| Agent | Model setting | Responsibility |
|---|---|---|
| **Router** | `GEMINI_MODEL_ROUTER` | Classifies the message (`question` / `clarification` / `acknowledgment` / `correction`) and decides whether the board is needed at all (e.g. "thanks!" needs no vision). |
| **Vision Parser** | `GEMINI_MODEL_VISION` | Full screenshot → structured board JSON (equations, text, problem statements, shapes, relationships, warnings). |
| **Vision Patch** | `GEMINI_MODEL_VISION` | Analyses a high-resolution crop of only the changed region and merges the result into the stored context. |
| **Context Filter** | `GEMINI_MODEL_FILTER` | Selects only the board elements relevant to the question + current viewport before they reach the tutor. |
| **Tutor** | `GEMINI_MODEL_TUTOR` | Pedagogical answer using history, filtered board context, viewport hint and message metadata; may return a `todraw` plan. |
| **Draw** | `GEMINI_MODEL_DRAW` | Turns a `todraw` plan into Excalidraw elements placed to avoid overlaps. |

### Board context

Instead of re-sending screenshots, the board is stored as a compact **structured JSON context**
(`BOARD_CONTEXT` message) — elements with ids, types, positions, `patch_bbox`, plus
`problem_statements_summary`, `relationships` and `board_warnings`. It is built incrementally
by the vision agents and reused by later turns, so a chat turn on an unchanged board costs **zero
vision calls**.

### Deterministic (non-AI) helpers

- **Viewport intersection** — which elements are on screen is computed in pure Python from
  `patch_bbox` ↔ viewport rectangles (no model call).
- **Signature-based deduplication** — equations, text, problem statements and shapes get a normalised
  content signature so repeated detections update an element in place instead of duplicating it.
- **Safe fallbacks everywhere** — router parse error → assume the board is needed; filter failure →
  full context; malformed tutor JSON → salvage the `message` field from the raw text. The filter can
  only ever *save* tokens, never break an answer.

---

## Database Architecture

PostgreSQL 16, managed with Alembic migrations (`backend/alembic/versions`). Identifiers are
string UUIDs; timestamps are timezone-aware.

```mermaid
erDiagram
    User ||--o{ Board : owns
    User ||--o{ BoardConversation : starts
    User ||--o{ AssistantMessage : writes
    User ||--o{ GeneratedNodeProposal : requests
    Board ||--o{ BoardSnapshot : "has versions"
    Board ||--o{ BoardConversation : has
    Board ||--o{ AssistantMessage : has
    Board ||--o{ GeneratedNodeProposal : has
    BoardConversation ||--o{ AssistantMessage : contains

    User {
        string id PK
        string email UK
        string clerkId UK
        timestamptz createdAt
        timestamptz updatedAt
    }
    Board {
        string id PK
        string ownerId FK
        string title
        bool isDeleted
        timestamptz deletedAt
        timestamptz purgeAt
        timestamptz lastOpenedAt
        timestamptz updatedAt
    }
    BoardSnapshot {
        string id PK
        string boardId FK
        int version
        jsonb sceneJson
        string savedByUserId
        timestamptz createdAt
    }
    BoardConversation {
        string id PK
        string boardId FK
        string userId FK
        string title
        timestamptz updatedAt
    }
    AssistantMessage {
        string id PK
        string boardId FK
        string userId FK
        string conversationId FK "nullable"
        string role "USER or ASSISTANT"
        string kind "CHAT or BOARD_CONTEXT"
        string status
        text content
        timestamptz createdAt
    }
    GeneratedNodeProposal {
        string id PK
        string boardId FK
        string requestedByUserId FK
        jsonb proposalJson
        timestamptz expiresAt
        timestamptz acceptedAt
    }
```

### Table notes

| Table | Purpose & design decisions |
|---|---|
| **User** | Local mirror of the Clerk identity (`clerkId` unique). Created on first authenticated request. |
| **Board** | Owned by a user. **Soft delete** via `isDeleted` / `deletedAt` / `purgeAt` with a 30-day restore window; index on `(ownerId, updatedAt)` for the boards list. |
| **BoardSnapshot** | Immutable, versioned Excalidraw scene stored as **JSONB**. `UNIQUE (boardId, version)` is the backbone of optimistic concurrency. Only the newest `SNAPSHOT_RETENTION` (default 50) versions are kept per board. |
| **BoardConversation** | A chat thread within a board (history feature). Indexed on `(boardId, updatedAt)` and `userId`. Cascade-deletes its messages. |
| **AssistantMessage** | Single table for two kinds of rows: `CHAT` (user/assistant text, belongs to a conversation) and `BOARD_CONTEXT` (JSON snapshot of the parsed board, not tied to a conversation — the board's understanding is shared across threads). Indexed on `(boardId, createdAt)` and `(conversationId, createdAt)`. |
| **GeneratedNodeProposal** | Schema for persisted AI draw proposals with expiry/acceptance tracking (reserved; proposals are currently handled client-side). |

### Data-integrity rules

- All foreign keys use `ON DELETE CASCADE` — purging a board removes snapshots, conversations,
  messages and proposals automatically.
- **Optimistic concurrency for snapshots:** the server computes `latest + 1` and inserts. If two
  writers collide, the unique constraint raises `IntegrityError`; the loser rolls back, re-reads the
  latest version and retries (up to 5 times). A `staleWarning` flag is returned when the client's
  `baseVersion` is older than the latest saved version.
- **Ownership checks** on every board-scoped endpoint (`404` for missing, `403` for foreign boards).
- **Legacy migration** — pre-history chat messages without a conversation are folded into an
  automatically created conversation on first listing.
- **Maintenance:** `python -m app.cli purge-boards` permanently deletes boards whose `purgeAt` has
  passed (intended for a daily cron).

---

## API Reference

Interactive docs are available at `http://127.0.0.1:8000/docs` when the backend is running.
All routes except `/health` require a Clerk bearer token.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/boards` | List the user's non-deleted boards |
| `POST` | `/boards` | Create a board |
| `DELETE` | `/boards/{id}` | Soft-delete (restorable for 30 days) |
| `POST` | `/boards/{id}/restore` | Restore a soft-deleted board |
| `GET` | `/boards/{id}/snapshot` | Latest snapshot (`404` if none yet) |
| `PUT` | `/boards/{id}/snapshot` | Save a new version (`baseVersion`, `sceneJson`) → `{version, staleWarning}` |
| `GET` | `/boards/{id}/assistant/conversations` | List chat threads (with message count + preview) |
| `POST` | `/boards/{id}/assistant/conversations` | Create a chat thread |
| `GET` | `/boards/{id}/assistant/conversations/{cid}/messages` | Messages of a thread |
| `DELETE` | `/boards/{id}/assistant/conversations/{cid}` | Delete a thread |
| `POST` | `/boards/{id}/assistant/vision-sync` | Analyse a board patch/screenshot and update the stored board context |
| `POST` | `/boards/{id}/assistant/chat` | Non-streaming tutor reply |
| `POST` | `/boards/{id}/assistant/chat/stream` | **SSE** tutor reply (`status`, `delta`, `done`, `error` events) |
| `POST` | `/boards/{id}/assistant/draw` | Convert a `todraw` plan into Excalidraw elements |

AI endpoints share a per-user rate limit (`AI_RATE_LIMIT_PER_MINUTE`, default 20) and return structured
errors `{message, service, code}` (`AI_ERROR`, `VALIDATION_ERROR`, `INTERNAL_ERROR`).

---

## Frontend Architecture

```
frontend/src
├── app/                    # App Router: landing, auth pages, /boards, /boards/[boardId]
├── components/
│   ├── whiteboard/         # Excalidraw canvas, workspace, draw-proposal bar, stale-state banner
│   ├── sidebar/            # AI assistant sidebar + markdown/LaTeX message renderer
│   ├── board-list/         # Boards list and actions
│   └── providers/          # Clerk + TanStack Query providers
├── hooks/
│   ├── useBoardAutosave    # debounced, versioned persistence + flush on page hide
│   ├── useBoardVisionSync  # change tracking by element version, idle debounce, cooldown
│   ├── useAssistantChat    # SSE streaming client + conversation state
│   ├── useAssistantDraw    # draw proposals
│   └── useApiClient        # authenticated fetch wrapper (Clerk token)
└── lib/                    # Excalidraw export/sanitising, API client, Zod validation
```

**Vision sync strategy (token-conscious by design):**

- Each element's Excalidraw `version` is tracked; only elements with a newer version than the last
  analysed one count as *changed*.
- Background analysis fires after **3 s of idle** and at most once per **2 min** (cooldown).
- Sending a chat message forces an immediate sync of pending changes — but if nothing changed, **no
  image is sent** and the stored context is reused.
- Only the changed region is exported as a high-resolution crop (patch), not the whole canvas.

---

## Engineering Highlights

- **Streaming JSON extractor** — the tutor answers in JSON (`message` + `todraw`). A custom
  incremental parser (`StreamingJsonStringExtractor`) streams the `message` text to the UI while the
  JSON is still arriving, decodes escapes on the fly and *disambiguates LaTeX from JSON escapes*
  (`\n` vs `\neq`, `\frac`, `\beta` …).
- **Resilient LLM calls** — retry with exponential backoff only for transient 503s (and only before the
  first streamed chunk, to avoid duplicated output); 429/quota errors fail fast with a clear message.
- **Model-agnostic request builder** — handles Gemma models that reject `system_instruction`
  by prepending the prompt as the first turn.
- **Concurrency-safe versioning** instead of locks — a unique constraint + retry loop.
- **Typed end to end** — Pydantic schemas on the API, Zod validation on the client.
- **Tests** — pytest for the backend, Vitest (unit/contract) and Playwright (E2E) for the frontend.

---

## Roadmap & Known Limitations

SmartStudy is a prototype; the following areas are known and planned:

- **Board parser (Vision Parser / Patch) — planned rewrite.**
  Today new analyses are merged into the stored context using content signatures. The next version
  should **overwrite updated elements** (matching by element identity/version rather than by
  re-detecting content), so edits to existing content *replace* the old entry instead of
  relying on dedupe heuristics, and it should be **optimised for token usage** (smaller schema,
  incremental updates, no redundant re-parsing).
- **AI tutor context filtering — prototype.**
  The Context Filter agent is a first iteration (one extra LLM call that prunes the board JSON by
  relevance and viewport). It will be enhanced — e.g. cheaper deterministic pre-filtering, relevance
  scoring, and tighter token budgets — before being considered production-grade.
- Persisted draw proposals (`GeneratedNodeProposal`) are modelled but not yet wired end to end.
- Real-time collaboration (multi-user boards) is out of scope for now.
- Periodic purge of expired boards currently requires an external cron to run `app.cli`.

---

## Getting Started

### Prerequisites

- **Node.js** ≥ 20 and npm
- **Python** ≥ 3.11
- **Docker** & Docker Compose (local PostgreSQL)
- A [Clerk](https://clerk.com/) application and a [Google AI Studio](https://aistudio.google.com/) API key

### 1. Database

```bash
npm run db:up        # docker compose up -d postgres (postgres:16, db "whiteboard")
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in DATABASE_URL, Clerk and Gemini credentials
cd ..
npm run db:migrate            # alembic upgrade head
npm run dev:api               # http://127.0.0.1:8000  (docs: /docs)
```

Example `DATABASE_URL` for the bundled Compose database:
`postgresql+asyncpg://app:password@localhost:5432/whiteboard`

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env          # Clerk publishable + secret key, NEXT_PUBLIC_API_URL
cd ..
npm run dev                   # http://localhost:3000
```

### Root scripts

| Command | Description |
|---|---|
| `npm run dev` | Frontend dev server |
| `npm run dev:api` | Backend dev server (uvicorn `--reload`) |
| `npm run build` | Frontend production build |
| `npm run lint` | Frontend lint |
| `npm run test` | Frontend unit/contract tests (Vitest) |
| `npm run test:e2e` | Playwright E2E tests |
| `npm run db:up` / `db:down` | Start / stop PostgreSQL |
| `npm run db:migrate` | Apply Alembic migrations |
| `npm run db:stamp` | Stamp the current Alembic revision |

---

## Configuration

### Backend (`backend/.env`)

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://…` connection string | — (required) |
| `CLERK_JWKS_URL` | Clerk JWKS endpoint for JWT verification | — (required) |
| `CLERK_SECRET_KEY` | Clerk secret key | — |
| `CLERK_ISSUER` | If set, JWT `iss` must match | — |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` |
| `GEMINI_API_KEY` | Google Gemini API key | — |
| `GEMINI_MODEL_ROUTER` / `_VISION` / `_FILTER` / `_TUTOR` / `_DRAW` | Model per agent | see `app/config.py` |
| `AI_RATE_LIMIT_PER_MINUTE` | AI requests per user per minute | `20` |
| `SNAPSHOT_RETENTION` | Snapshot versions kept per board | `50` |
| `GEMINI_MAX_ATTEMPTS` | Attempts on transient 503 errors | `3` |

### Frontend (`frontend/.env`)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk client key |
| `CLERK_SECRET_KEY` | Clerk server key |
| `NEXT_PUBLIC_API_URL` | Backend URL (default `http://127.0.0.1:8000`) |

> Never commit `.env` files — only `.env.example` templates are tracked.

---

## Testing

```bash
npm run test                       # frontend (Vitest)
npm run test:e2e                   # frontend (Playwright)
cd backend && .venv/bin/pytest     # backend
```

---

## Repository Structure

```
SmartStudy/
├── frontend/             # Next.js 15 app (src/, tests/)
├── backend/
│   ├── app/
│   │   ├── routers/      # boards, snapshots, assistant
│   │   ├── services/     # boards, snapshots, assistant, gemini (AI pipeline)
│   │   ├── models.py     # SQLAlchemy models
│   │   ├── schemas.py    # Pydantic schemas
│   │   ├── prompts.py    # Agent system prompts
│   │   ├── formatting.py # LaTeX-safe tutor message formatting
│   │   ├── auth.py       # Clerk JWT verification
│   │   ├── ratelimit.py  # Per-user AI rate limiting
│   │   └── cli.py        # Maintenance commands (purge-boards)
│   ├── alembic/          # Migrations (0001 schema, 0002 unique version, 0003 conversations)
│   └── tests/
├── specs/                # Product specifications
├── docker-compose.yml    # Local PostgreSQL
└── package.json          # Root orchestration scripts
```
