# Research: SmartStudy Learning Boards Platform

## Decision 1: Whiteboard engine = free Excalidraw package

- **Decision**: Use `@excalidraw/excalidraw` as the embedded whiteboard engine.
- **Rationale**: It is free, mature, and provides the needed feature set from the
  spec (draw, shapes, connectors, text, image, erase, zoom, undo/redo) with less
  custom canvas implementation risk.
- **Alternatives considered**:
  - Build a custom canvas/SVG editor: rejected due to high complexity and slower
    delivery.
  - tldraw free tier: rejected for v1 because Excalidraw has lower integration
    friction for this scope.

## Decision 2: Persistence in local PostgreSQL

- **Decision**: Persist users, boards, board metadata, board scene snapshots, and
  assistant Q/A history in a local PostgreSQL database.
- **Rationale**: PostgreSQL gives relational integrity, transaction support, and
  clear path to production migration while satisfying the explicit local storage
  requirement.
- **Alternatives considered**:
  - SQLite: rejected due to weaker concurrency posture and migration path for
    expected multi-user usage.
  - File-based scene storage only: rejected because querying dashboard metadata
    (search/filter/sort/favorites/recency) would become error-prone.

## Decision 3: ORM and schema management

- **Decision**: Use Prisma ORM and migrations for database access.
- **Rationale**: Type-safe queries in TypeScript strict mode, robust migration
  workflow, and efficient developer ergonomics for local PostgreSQL.
- **Alternatives considered**:
  - Raw SQL only: rejected to avoid repetitive boilerplate and reduce mismatch
    risk between schema and application models.
  - Drizzle ORM: viable, but Prisma selected for wider team familiarity.

## Decision 4: Authentication approach

- **Decision**: Use Auth.js (NextAuth) with credentials provider for v1.
- **Rationale**: Matches spec assumptions (email/password pattern), integrates
  cleanly with Next.js App Router route handlers and session checks.
- **Alternatives considered**:
  - Custom JWT/session from scratch: rejected for unnecessary security surface.
  - Third-party managed auth platform: deferred until hosting and budget choices.

## Decision 5: Board scene storage format

- **Decision**: Store Excalidraw scene payload as versioned JSON snapshots per
  board, plus metadata fields (`updatedAt`, editor user, scene version).
- **Rationale**: Keeps schema flexible while preserving recoverability and audit
  of changes for undo/reload semantics.
- **Alternatives considered**:
  - Store each stroke as relational rows: rejected for v1 complexity.
  - Store only latest binary export: rejected because assistant context extraction
    and partial scene operations need structured data.

## Decision 6: Assistant grounding strategy

- **Decision**: Build a server-side assistant orchestration service that combines:
  board scene summary + recent user question history + current prompt.
- **Rationale**: Ensures grounding in visible board context and keeps prompt logic
  out of UI components.
- **Alternatives considered**:
  - Direct client-side LLM calls: rejected due to secret exposure risk and weaker
    policy enforcement.
  - Generic chat without board context: rejected because it fails FR-011.

## Decision 7: API contract style

- **Decision**: Define REST-style route contracts for auth/session checks, board
  CRUD, scene persistence, and assistant interaction.
- **Rationale**: Fits Next.js route handlers, easy to test, and explicit for
  frontend React Query integration.
- **Alternatives considered**:
  - GraphQL: rejected for v1 overhead without clear multi-client need.
  - Server Actions only: partially useful, but explicit route contracts are
    preferred for contract tests and clearer boundaries.

## Decision 8: Testing strategy

- **Decision**: Layered tests with Vitest (unit/integration), Playwright (E2E),
  and contract tests for API routes and schema validation.
- **Rationale**: Covers constitution-critical logic paths and user-visible
  behavior while keeping tests resistant to implementation churn.
- **Alternatives considered**:
  - Snapshot-heavy UI tests: rejected due to brittleness and low behavioral value.
