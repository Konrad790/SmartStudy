# Quickstart: SmartStudy Learning Boards Platform

## Prerequisites

- Node.js 20+
- pnpm (or npm/yarn equivalent)
- Docker (recommended) for local PostgreSQL

## 1) Start local PostgreSQL

Example Docker command:

```bash
docker run --name smartstudy-postgres \
  -e POSTGRES_USER=smartstudy \
  -e POSTGRES_PASSWORD=smartstudy \
  -e POSTGRES_DB=smartstudy \
  -p 5432:5432 \
  -d postgres:16
```

## 2) Configure environment

Create `.env.local` with values equivalent to:

```bash
DATABASE_URL=postgresql://smartstudy:smartstudy@localhost:5432/smartstudy
AUTH_SECRET=replace-with-random-secret
```

Add assistant provider variables according to chosen backend provider when
implementing assistant route handlers.

## 3) Install dependencies

```bash
pnpm install
```

## 4) Initialize database schema

```bash
pnpm prisma migrate dev
```

## 5) Run the app

```bash
pnpm dev
```

Open `http://localhost:3000`.

## 6) Validate critical flows

1. Register/sign in from the sign-in page matching `design/sign-in.png`.
2. Create a board from dashboard (`design/dashboard.png`).
3. Open the board workspace and draw using Excalidraw tools.
4. Refresh and confirm board content persists from PostgreSQL.
5. Ask a board-grounded assistant question and verify non-destructive error
   behavior if assistant service is unavailable.

## 7) Run tests (after implementation)

```bash
pnpm test
pnpm test:e2e
```
