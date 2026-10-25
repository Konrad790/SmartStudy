# Research: Whiteboard MVP Foundation

## Decision 1: Whiteboard engine

- **Decision**: Use `@excalidraw/excalidraw` for the infinite canvas and drawing
  interactions.
- **Rationale**: Mature open-source package that covers node-like drawing
  elements, connectors, zoom/pan, and responsive behavior with low implementation
  risk and no paid licensing requirements for MVP.
- **Alternatives considered**:
  - Custom canvas stack: rejected due to high complexity and slower MVP delivery.
  - Paid whiteboard SDKs: rejected to minimize infrastructure/tooling costs.

## Decision 2: Persistence layer

- **Decision**: Use local PostgreSQL as the system of record via Prisma ORM.
- **Rationale**: Strong transactional guarantees for board snapshots, deletion
  policy, and user ownership while staying open-source and low-cost in local
  deployment.
- **Alternatives considered**:
  - Managed cloud databases: deferred to post-MVP cost phase.
  - SQLite only: rejected for weaker concurrency and migration path.

## Decision 3: Autosave strategy

- **Decision**: Debounced autosave during active editing plus final save attempt
  on page exit/navigation.
- **Rationale**: Balances UX responsiveness and database write volume; aligns with
  clarified spec acceptance criteria.
- **Alternatives considered**:
  - Save every change: rejected due to excessive write amplification.
  - Fixed-interval only: rejected due to larger data loss windows.

## Decision 4: Conflict handling

- **Decision**: Last-write-wins with stale-state warning and explicit refresh
  prompt.
- **Rationale**: Keeps logic simple for MVP while giving users clear feedback when
  another session has changed the board.
- **Alternatives considered**:
  - Session locks: rejected for UX friction.
  - Manual merge engine: rejected as out-of-scope complexity.

## Decision 5: AI inference strategy

- **Decision**: Use local LLM inference through Ollama by default, with model
  choices including Llama and Qwen families.
- **Rationale**: Satisfies cost-minimization and open-source preference; supports
  offline/local experimentation and no mandatory paid AI APIs in MVP.
- **Alternatives considered**:
  - Hosted-only providers (OpenAI/Anthropic/etc.): deferred to later phase.
  - Build custom model serving stack: rejected due to maintenance overhead.

## Decision 6: AI provider migration path

- **Decision**: Introduce an AI provider adapter interface with at least two
  implementations: `ollama-provider` and `hosted-provider` (stub/optional).
- **Rationale**: Prevents coupling AI workflows to one provider and enables later
  migration with minimal domain/service refactors.
- **Alternatives considered**:
  - Direct calls from route handlers: rejected due to lock-in and duplication.

## Decision 7: Auth and privacy posture

- **Decision**: Require authentication for all board and AI actions and enforce
  per-user private board access.
- **Rationale**: Matches clarifications and protects user data for persisted
  boards/assistant history.
- **Alternatives considered**:
  - Anonymous boards: rejected due to ownership/security ambiguity.

## Decision 8: Cost controls

- **Decision**: Keep MVP runtime local/self-hosted baseline, avoid paid enterprise
  services, and keep observability to lightweight open-source logging/metrics.
- **Rationale**: Reduces recurring spend and supports rapid iteration.
- **Alternatives considered**:
  - Enterprise SaaS observability/workflow platforms: deferred until scale
    requires them.
