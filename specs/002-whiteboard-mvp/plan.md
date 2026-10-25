# Implementation Plan: Whiteboard MVP Foundation

**Branch**: `003-whiteboard-mvp` | **Date**: 2026-05-12 | **Spec**: `specs/002-whiteboard-mvp/spec.md`
**Input**: Feature specification from `/specs/002-whiteboard-mvp/spec.md`

## Summary

Deliver a stable whiteboard-first MVP with board lifecycle, infinite canvas,
node/connection editing, zoom/pan, autosave persistence, and an assistant sidebar
that can generate node suggestions and summarize board content. The architecture
prioritizes low-cost local deployment and open-source tooling by default: local
PostgreSQL for persistence and local LLM inference via Ollama (Llama/Qwen), with
an AI provider abstraction that allows later migration to hosted providers
without redesigning domain logic.

## Technical Context

**Language/Version**: TypeScript (strict), Node.js 20+  
**Primary Dependencies**: Next.js App Router, React, TailwindCSS, shadcn/ui, TanStack React Query, Zod, Excalidraw (`@excalidraw/excalidraw`), Prisma, Auth.js, Ollama local API client  
**Storage**: Local PostgreSQL (primary source of truth), optional local disk for exports  
**Testing**: Vitest + Testing Library, Playwright E2E, contract tests for route handlers and AI adapter boundaries  
**Target Platform**: Web app for modern desktop/mobile browsers on self-hosted or local runtime  
**Project Type**: Single Next.js web application  
**Performance Goals**: Canvas interactions remain fluid for typical boards; 95% autosave writes complete within 2s idle window; dashboard load under 2s on local network  
**Constraints**: Prefer free/open-source tools; minimize infrastructure costs; avoid paid enterprise services in MVP; local LLMs via Ollama with Llama/Qwen; architecture must support later hosted AI migration  
**Scale/Scope**: MVP single-user editing per board session (no realtime collaboration), hundreds of users, thousands of boards, assistant usage tied to board context only

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

- Mandatory stack aligns with constitution and project constraints.
- Business logic will live in `src/server/*` (services/repositories/adapters).
- Excalidraw will be isolated to focused client components.
- AI integration is designed with provider abstraction to avoid lock-in and
  preserve migration path.

## Project Structure

### Documentation (this feature)

```text
specs/002-whiteboard-mvp/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── whiteboard-api.yaml
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
│   ├── boards/
│   │   ├── page.tsx
│   │   └── [boardId]/page.tsx
│   └── api/
│       ├── boards/
│       ├── boards/[boardId]/snapshot/
│       ├── boards/[boardId]/assistant/chat/
│       └── boards/[boardId]/assistant/generate/
├── components/
│   ├── whiteboard/
│   ├── sidebar/
│   └── board-list/
├── hooks/
├── lib/
│   ├── validation/
│   ├── api-client/
│   └── constants/
├── server/
│   ├── services/
│   ├── repositories/
│   ├── ai/
│   │   ├── provider.ts
│   │   ├── ollama-provider.ts
│   │   └── hosted-provider.ts
│   ├── auth/
│   └── db/
└── types/

prisma/
├── schema.prisma
└── migrations/

tests/
├── unit/
├── integration/
├── contract/
└── e2e/
```

**Structure Decision**: Single Next.js codebase with clear separation:
presentation in `src/app` + `src/components`, domain/infrastructure in
`src/server`, and AI provider adapter boundaries in `src/server/ai`.

## Phase 0: Research Output

See `research.md`. Key decisions:

- Use open-source Excalidraw for whiteboard UX.
- Persist state in local PostgreSQL via Prisma.
- Use Ollama for local inference with Llama/Qwen defaults.
- Add provider abstraction to support migration to hosted AI providers later.
- Avoid paid enterprise dependencies in MVP baseline.

## Phase 1: Design Output

- Data model: `data-model.md`
- API contracts: `contracts/whiteboard-api.yaml`
- Quickstart: `quickstart.md`
- Agent context updated to point to this plan file.

## Post-Design Constitution Check

**Result**: PASS

- Stack and coding constraints align with constitution.
- Business logic remains outside components in server modules/hooks.
- Validation, loading/error states, and typed API boundaries are included in
  contracts/design.
- Performance and testing expectations are measurable in the spec and plan.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
