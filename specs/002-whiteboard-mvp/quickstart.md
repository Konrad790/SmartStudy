# Quickstart: Whiteboard MVP Foundation

## Prerequisites

- Node.js 20+
- pnpm
- Docker (recommended for local PostgreSQL and Ollama)

## 1) Start local PostgreSQL

```bash
docker run --name smartstudy-postgres \
  -e POSTGRES_USER=smartstudy \
  -e POSTGRES_PASSWORD=smartstudy \
  -e POSTGRES_DB=smartstudy \
  -p 5432:5432 \
  -d postgres:16
```

## 2) Start local Ollama

Install Ollama locally and pull at least one open model:

```bash
ollama pull llama3.1:8b
ollama pull qwen2.5:7b
```

Ensure Ollama is reachable on default local endpoint.

## 3) Configure environment

Create `.env.local`:

```bash
DATABASE_URL=postgresql://smartstudy:smartstudy@localhost:5432/smartstudy
AUTH_SECRET=replace-with-random-secret
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
AI_PROVIDER=ollama
```

For later hosted migration, `AI_PROVIDER` can switch while retaining app-level
AI service interfaces.

## 4) Install dependencies and migrate database

```bash
pnpm install
pnpm prisma migrate dev
```

## 5) Run application

```bash
pnpm dev
```

Open `http://localhost:3000`.

## 6) Verify MVP flows

1. Sign in and create a board.
2. Add/move nodes and connections, zoom/pan the canvas.
3. Wait briefly and reload to verify debounced autosave restore.
4. Open a second tab and validate stale-state warning behavior.
5. Use assistant sidebar:
   - chat
   - generate node proposal
   - confirm insertion
   - summarize board
6. Delete board and verify soft-delete + restore behavior.

## 7) Run tests

```bash
pnpm test
pnpm test:e2e
```

## 8) Ops notes

- AI provider defaults to local Ollama (`AI_PROVIDER=ollama`).
- For hosted migration later, keep service interfaces unchanged and switch only
  provider wiring/env values.
- Run expired-board cleanup periodically via `purgeExpiredDeletedBoards()`.
