# Implementation Plan: SmartStudy Learning Boards Platform

**Branch**: `main` | **Date**: 2026-05-12 | **Spec**: `specs/001-smartstudy-platform/spec.md`
**Input**: Feature specification from `/specs/001-smartstudy-platform/spec.md`

## Summary

Build SmartStudy as a Next.js web application where learners authenticate, manage
boards on a dashboard, draw in a board workspace, and ask an AI tutor questions
grounded in the current board content. The whiteboard engine will use the free
Excalidraw package embedded as a client-side board component, while user, board,
canvas, and assistant data are persisted in a local PostgreSQL database.

## Technical Context

**Language/Version**: TypeScript (strict) on Node.js 20+  
**Primary Dependencies**: Next.js App Router, React, TailwindCSS, shadcn/ui, TanStack React Query, Zod, Excalidraw (free package), Prisma ORM, NextAuth/Auth.js  
**Storage**: Local PostgreSQL (development and initial deployment baseline)  
**Testing**: Vitest + Testing Library (unit/integration), Playwright (E2E), Prisma test database reset  
**Target Platform**: Web (desktop and mobile browsers), local/self-hosted runtime for v1  
**Project Type**: Single Next.js web application  
**Performance Goals**: Dashboard first meaningful render under 2s on typical broadband; board interaction remains fluid at 60fps for common board sizes; assistant response initiation under 3s median  
**Constraints**: Must align with `design/` mockups; Client Components only where required (Excalidraw and interactive UI); no `any`; OWASP-minded auth and input handling; avoid duplicate server requests  
**Scale/Scope**: v1 single-tenant local deployment, hundreds of users, thousands of boards, no real-time collaboration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Per `.specify/memory/constitution.md` (SmartStudy):

- **Stack**: Next.js App Router, TypeScript strict mode, TailwindCSS, shadcn/ui,
  TanStack React Query, Zod.
- **Architecture**: Business logic outside React components; hooks for reusable
  client logic; composition over inheritance; shared logic centralized; avoid
  deep component trees.
- **React**: Prefer Server Components; Client Components require explicit
  justification; controlled forms; semantic HTML; accessibility mandatory;
  minimize unnecessary `useEffect` and prop drilling.
- **Data**: Validate external/API data with Zod; typed responses; React Query
  for server state; centralized API clients; explicit loading, empty, and error
  states; avoid duplicate in-flight requests.
- **Styling**: Tailwind only (no inline styles for routine UI); mobile-first;
  consistent spacing and typography; design tokens where they reduce drift.
- **Quality & security**: No `any`; no client-side secrets; sanitize user input;
  validate forms; OWASP-minded practices.
- **Performance**: Minimize client JS; lazy-load heavy client modules when it
  helps initial load; avoid unnecessary re-renders; optimize images and assets.
- **Process**: Spec → plan → tasks before feature coding; refactors preserve
  behavior unless the spec changes; critical logic covered by meaningful tests.

If any gate cannot be met, document the exception and rationale in **Complexity
Tracking** below.

**Initial Gate Result**: PASS

- Planned stack exactly follows constitution requirements.
- Excalidraw integration is isolated to justified Client Components.
- Business logic will be placed in server/domain modules (`src/server/*`), not UI components.
- External inputs (API payloads, assistant output envelopes) are validated with Zod.
- No constitution exceptions are required at planning time.

## Project Structure

### Documentation (this feature)

```text
specs/001-smartstudy-platform/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── smartstudy-api.yaml
└── tasks.md
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
src/
├── app/
│   ├── (auth)/
│   │   ├── sign-in/page.tsx
│   │   └── register/page.tsx
│   ├── dashboard/page.tsx
│   ├── boards/[boardId]/page.tsx
│   └── api/
│       ├── boards/route.ts
│       ├── boards/[boardId]/route.ts
│       ├── boards/[boardId]/scene/route.ts
│       └── boards/[boardId]/assistant/route.ts
├── components/
│   ├── auth/
│   ├── dashboard/
│   ├── board/
│   └── ai/
├── hooks/
│   ├── useBoardsQuery.ts
│   ├── useBoardScene.ts
│   └── useAssistantChat.ts
├── lib/
│   ├── api-client/
│   ├── validation/
│   └── utils/
├── server/
│   ├── auth/
│   ├── db/
│   ├── repositories/
│   ├── services/
│   └── ai/
└── styles/

prisma/
├── schema.prisma
└── migrations/

tests/
├── unit/
├── integration/
├── contract/
└── e2e/
```

**Structure Decision**: Single-project Next.js app with clear separation between
UI (`src/app`, `src/components`) and business logic (`src/server`). This keeps
client-heavy Excalidraw isolated while preserving server-centric architecture.

## Phase 0: Research Summary

See `research.md` for detailed decisions. Key outcomes:

- Use free Excalidraw package (`@excalidraw/excalidraw`) for canvas interactions.
- Persist board scene JSON snapshots and metadata in local PostgreSQL via Prisma.
- Use Auth.js with credentials provider for initial email/password access.
- Use a server-side assistant service with board-context prompt construction and
  structured response validation.

## Phase 1: Design Artifacts

- Data model: `data-model.md`
- API contracts: `contracts/smartstudy-api.yaml`
- Developer quickstart: `quickstart.md`
- Agent context updated in `.cursor/rules/specify-rules.mdc`

## Post-Design Constitution Check

**Result**: PASS

- Excalidraw is used as a focused client island; the rest remains server-first.
- Shared logic (auth, board persistence, assistant orchestration) is centralized
  under `src/server`.
- API contracts and response validation rely on Zod-first boundary checks.
- Testing plan includes critical-path auth, board persistence, and assistant flows.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
