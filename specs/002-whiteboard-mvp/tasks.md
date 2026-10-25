# Tasks: Whiteboard MVP Foundation

**Input**: Design documents from `/specs/002-whiteboard-mvp/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Include automated tests for critical business logic and user-visible
outcomes per `.specify/memory/constitution.md`. Omit tests only when the feature
specification explicitly excludes them. Prefer behavior-focused tests; avoid
brittle snapshot-only coverage.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Single project paths under `src/`, `prisma/`, and `tests/`
- API contracts from `specs/002-whiteboard-mvp/contracts/whiteboard-api.yaml`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and baseline tooling.

- [x] T001 Initialize Next.js TypeScript project scaffold and scripts in `package.json`
- [x] T002 Install MVP dependencies (Tailwind, shadcn/ui, React Query, Zod, Excalidraw, Prisma, Auth.js) in `package.json`
- [x] T003 [P] Configure linting, formatting, and strict TS settings in `tsconfig.json` and `.eslintrc.*`
- [x] T004 [P] Add environment variable schema and defaults in `src/lib/validation/env.ts` and `.env.example`
- [x] T005 [P] Configure base app layout, theme provider, and dark mode tokens in `src/app/layout.tsx` and `src/styles/globals.css`
- [x] T006 [P] Create initial directory structure placeholders per plan in `src/components/`, `src/server/`, `src/hooks/`, and `tests/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T007 Define Prisma schema for `User`, `Board`, `BoardSnapshot`, `AssistantMessage`, and `GeneratedNodeProposal` in `prisma/schema.prisma`
- [x] T008 Run and commit initial migrations in `prisma/migrations/`
- [x] T009 [P] Implement Prisma client and DB module wiring in `src/server/db/client.ts`
- [x] T010 [P] Implement Auth.js server configuration and session helpers in `src/server/auth/config.ts` and `src/server/auth/session.ts`
- [x] T011 [P] Add shared API response/error envelope utilities in `src/lib/api-client/http.ts` and `src/lib/utils/api-errors.ts`
- [x] T012 [P] Add Zod DTOs for board, snapshot, and assistant payload validation in `src/lib/validation/board.ts` and `src/lib/validation/assistant.ts`
- [x] T013 Implement AI provider abstraction interface in `src/server/ai/provider.ts`
- [x] T014 Implement local Ollama adapter (Llama/Qwen-compatible) in `src/server/ai/ollama-provider.ts`
- [x] T015 Implement hosted-provider placeholder adapter for future migration in `src/server/ai/hosted-provider.ts`
- [x] T016 Implement AI provider factory by `AI_PROVIDER` env in `src/server/ai/index.ts`
- [x] T017 Create base route auth/ownership guard helpers in `src/server/services/authorization-service.ts`
- [x] T018 [P] Add contract test harness setup for API routes in `tests/contract/helpers/http-client.ts`
- [x] T019 [P] Add Playwright baseline auth fixture and seeded test user in `tests/e2e/fixtures/auth.fixture.ts`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Create and manage boards (Priority: P1) 🎯 MVP

**Goal**: Authenticated users can create, list, open, soft-delete, and restore boards.

**Independent Test**: Create two boards, open one, soft-delete one, restore it within 30 days, and verify ownership boundaries are enforced.

### Tests for User Story 1

- [x] T020 [P] [US1] Add contract tests for `GET/POST /api/boards` in `tests/contract/boards.list-create.contract.test.ts`
- [x] T021 [P] [US1] Add contract tests for `DELETE /api/boards/{boardId}` and `POST /api/boards/{boardId}/restore` in `tests/contract/boards.delete-restore.contract.test.ts`
- [x] T022 [P] [US1] Add integration tests for board ownership guards in `tests/integration/board-authorization.integration.test.ts`
- [x] T023 [P] [US1] Add E2E scenario for create/open/delete/restore flow in `tests/e2e/boards-lifecycle.e2e.spec.ts`

### Implementation for User Story 1

- [x] T024 [P] [US1] Implement board repository methods (list/create/soft-delete/restore) in `src/server/repositories/board-repository.ts`
- [x] T025 [US1] Implement board service with 30-day restore policy in `src/server/services/board-service.ts`
- [x] T026 [US1] Implement `GET/POST /api/boards` route handler in `src/app/api/boards/route.ts`
- [x] T027 [US1] Implement `DELETE /api/boards/{boardId}` route handler in `src/app/api/boards/[boardId]/route.ts`
- [x] T028 [US1] Implement `POST /api/boards/{boardId}/restore` route handler in `src/app/api/boards/[boardId]/restore/route.ts`
- [x] T029 [P] [US1] Implement boards query/mutation hooks in `src/hooks/useBoardsQuery.ts`
- [x] T030 [P] [US1] Implement boards list UI and actions in `src/components/board-list/boards-list.tsx`
- [x] T031 [US1] Implement boards page wiring and navigation in `src/app/boards/page.tsx`
- [x] T032 [US1] Add restore-window UI states and deletion feedback in `src/components/board-list/board-actions.tsx`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Edit content on infinite canvas (Priority: P2)

**Goal**: Users can edit board content on an infinite canvas with node manipulation, connections, zoom, and pan.

**Independent Test**: Open a board, create/move elements and links, then zoom/pan while preserving interaction stability.

### Tests for User Story 2

- [x] T033 [P] [US2] Add integration tests for board scene validation and transform handling in `tests/integration/whiteboard-scene.integration.test.ts`
- [x] T034 [P] [US2] Add E2E interaction tests for canvas edit/zoom/pan flows in `tests/e2e/whiteboard-canvas.e2e.spec.ts`

### Implementation for User Story 2

- [x] T035 [P] [US2] Build Excalidraw wrapper component with controlled props in `src/components/whiteboard/excalidraw-canvas.tsx`
- [x] T036 [US2] Implement board workspace shell with responsive canvas layout in `src/components/whiteboard/board-workspace.tsx`
- [x] T037 [US2] Implement board detail route page in `src/app/boards/[boardId]/page.tsx`
- [x] T038 [P] [US2] Add whiteboard state hook for viewport/tool synchronization in `src/hooks/useWhiteboardState.ts`
- [x] T039 [US2] Implement dark-mode compatible whiteboard theming in `src/components/whiteboard/whiteboard-theme.ts`

**Checkpoint**: User Story 2 is independently functional and testable.

---

## Phase 5: User Story 3 - Autosave and persistence (Priority: P3)

**Goal**: Board edits autosave with debounced behavior, restore on reload, and stale-session warnings under last-write-wins.

**Independent Test**: Edit a board, pause for autosave, reload for restore, then open second session to validate stale warnings.

### Tests for User Story 3

- [x] T040 [P] [US3] Add contract tests for `GET/PUT /api/boards/{boardId}/snapshot` in `tests/contract/boards-snapshot.contract.test.ts`
- [x] T041 [P] [US3] Add integration tests for debounce and version conflict handling in `tests/integration/autosave-conflict.integration.test.ts`
- [x] T042 [P] [US3] Add E2E tests for autosave and stale warning in `tests/e2e/autosave-conflict.e2e.spec.ts`

### Implementation for User Story 3

- [x] T043 [P] [US3] Implement snapshot repository and versioned writes in `src/server/repositories/snapshot-repository.ts`
- [x] T044 [US3] Implement autosave service with last-write-wins signaling in `src/server/services/autosave-service.ts`
- [x] T045 [US3] Implement `GET/PUT /api/boards/{boardId}/snapshot` route handler in `src/app/api/boards/[boardId]/snapshot/route.ts`
- [x] T046 [P] [US3] Implement autosave hook (debounce + exit flush) in `src/hooks/useBoardAutosave.ts`
- [x] T047 [US3] Integrate stale-state warning banner and refresh prompt in `src/components/whiteboard/stale-state-banner.tsx`
- [x] T048 [US3] Connect autosave lifecycle into workspace component in `src/components/whiteboard/board-workspace.tsx`

**Checkpoint**: User Story 3 is independently functional and testable.

---

## Phase 6: User Story 4 - AI sidebar assistance for board content (Priority: P4)

**Goal**: Provide assistant chat, node-generation preview/confirm, and board summarization using local Ollama by default.

**Independent Test**: Ask chat questions, request node proposal and confirm insertion, and request summary; verify failures are non-destructive.

### Tests for User Story 4

- [x] T049 [P] [US4] Add contract tests for assistant endpoints in `tests/contract/assistant.contract.test.ts`
- [x] T050 [P] [US4] Add integration tests for AI provider adapter fallback behavior in `tests/integration/ai-provider.integration.test.ts`
- [x] T051 [P] [US4] Add E2E tests for assistant sidebar chat/generate/summary in `tests/e2e/assistant-sidebar.e2e.spec.ts`

### Implementation for User Story 4

- [x] T052 [P] [US4] Implement assistant message repository in `src/server/repositories/assistant-repository.ts`
- [x] T053 [P] [US4] Implement generated node proposal repository in `src/server/repositories/generated-proposal-repository.ts`
- [x] T054 [US4] Implement assistant orchestration service in `src/server/services/assistant-service.ts`
- [x] T055 [US4] Implement `POST /api/boards/{boardId}/assistant/chat` route in `src/app/api/boards/[boardId]/assistant/chat/route.ts`
- [x] T056 [US4] Implement `POST /api/boards/{boardId}/assistant/generate` route in `src/app/api/boards/[boardId]/assistant/generate/route.ts`
- [x] T057 [US4] Implement `POST /api/boards/{boardId}/assistant/generate/{proposalId}/confirm` route in `src/app/api/boards/[boardId]/assistant/generate/[proposalId]/confirm/route.ts`
- [x] T058 [US4] Implement `GET /api/boards/{boardId}/assistant/summary` route in `src/app/api/boards/[boardId]/assistant/summary/route.ts`
- [x] T059 [P] [US4] Implement assistant React Query hooks in `src/hooks/useAssistantChat.ts` and `src/hooks/useNodeGeneration.ts`
- [x] T060 [US4] Build assistant sidebar UI with error/loading/empty states in `src/components/sidebar/assistant-sidebar.tsx`
- [x] T061 [US4] Integrate node proposal preview + confirm UX in `src/components/sidebar/node-proposal-panel.tsx`
- [x] T062 [US4] Integrate assistant sidebar with board workspace in `src/components/whiteboard/board-workspace.tsx`

**Checkpoint**: User Story 4 is independently functional and testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening across all implemented stories.

- [x] T063 [P] Add accessibility audits and keyboard navigation fixes in `src/components/` and `src/app/boards/`
- [x] T064 [P] Add performance instrumentation/logging for autosave and assistant latency in `src/server/services/autosave-service.ts` and `src/server/services/assistant-service.ts`
- [x] T065 [P] Add security hardening checks (authorization + input sanitization) in `src/server/services/authorization-service.ts` and `src/lib/validation/`
- [x] T066 [P] Add migration script or scheduled purge task for expired soft-deleted boards in `src/server/services/board-purge-service.ts`
- [x] T067 Run quickstart verification and update operator notes in `specs/002-whiteboard-mvp/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Start immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories.
- **Phases 3-6 (US1-US4)**: Depend on Phase 2 completion; execute by priority or in parallel by team capacity.
- **Phase 7 (Polish)**: Depends on completion of selected user stories.

### User Story Dependencies

- **US1 (P1)**: First functional increment; no dependency on other stories after Foundation.
- **US2 (P2)**: Depends on Foundation and board access flows from US1.
- **US3 (P3)**: Depends on US2 canvas integration and US1 board ownership.
- **US4 (P4)**: Depends on US2 board context and US3 snapshot persistence.

### Within Each User Story

- Write failing tests first.
- Implement repositories/services before route handlers.
- Integrate hooks/UI after API contracts pass.
- Complete acceptance tests before moving to next story.

### Parallel Opportunities

- Phase 1 tasks marked `[P]` can run concurrently.
- Phase 2 adapter, validation, and harness tasks marked `[P]` can run concurrently.
- Contract/integration/E2E tests per story marked `[P]` can run concurrently.
- Repository and UI tasks in each story marked `[P]` can be split across developers.

---

## Parallel Example: User Story 3

```bash
Task: "T040 [US3] Contract tests in tests/contract/boards-snapshot.contract.test.ts"
Task: "T041 [US3] Integration tests in tests/integration/autosave-conflict.integration.test.ts"
Task: "T046 [US3] Autosave hook in src/hooks/useBoardAutosave.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Deliver Phase 3 (US1) and validate independently.
3. Demo private board lifecycle including soft-delete/restore.

### Incremental Delivery

1. Add US2 for core whiteboard UX.
2. Add US3 for robust autosave and conflict handling.
3. Add US4 for local-AI assistant features.
4. Finish with Phase 7 hardening.

### Parallel Team Strategy

1. Platform engineer: Phase 1-2 + API scaffolding.
2. Frontend engineer: US2 + UI parts of US3/US4.
3. Backend/AI engineer: US3 persistence + US4 assistant services/adapters.

---

## Notes

- All tasks follow required checklist format with IDs, labels, and file paths.
- `[P]` tasks indicate no direct file contention with dependent unfinished tasks.
- Local Ollama is the default AI runtime; hosted migration path is preserved via adapter tasks.
