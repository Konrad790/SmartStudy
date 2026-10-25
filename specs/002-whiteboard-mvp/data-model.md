# Data Model: Whiteboard MVP Foundation

## Entity: User

- **Purpose**: Authenticated owner of boards and assistant activity.
- **Fields**:
  - `id` (uuid, PK)
  - `email` (string, unique, required)
  - `passwordHash` (string, required)
  - `createdAt` (timestamp, required)
  - `updatedAt` (timestamp, required)
- **Relationships**:
  - One-to-many with `Board`
  - One-to-many with `AssistantMessage`

## Entity: Board

- **Purpose**: Top-level whiteboard workspace.
- **Fields**:
  - `id` (uuid, PK)
  - `ownerId` (uuid, FK -> User.id, required)
  - `title` (string, required, max 120)
  - `isDeleted` (boolean, required, default false)
  - `deletedAt` (timestamp, nullable)
  - `purgeAt` (timestamp, nullable) // 30-day soft-delete window
  - `lastOpenedAt` (timestamp, nullable)
  - `updatedAt` (timestamp, required)
  - `createdAt` (timestamp, required)
- **Relationships**:
  - One-to-many with `BoardSnapshot`
  - One-to-many with `AssistantMessage`

## Entity: BoardSnapshot

- **Purpose**: Persisted board scene for restore/autosave.
- **Fields**:
  - `id` (uuid, PK)
  - `boardId` (uuid, FK -> Board.id, required)
  - `version` (int, required)
  - `sceneJson` (jsonb, required)
  - `savedByUserId` (uuid, FK -> User.id, required)
  - `createdAt` (timestamp, required)
- **Rules**:
  - Autosave writes increment `version`.
  - Last-write-wins conflict policy based on latest committed version.

## Entity: BoardNode

- **Purpose**: Logical node abstraction for AI generation/summaries.
- **Fields**:
  - `id` (uuid, PK)
  - `boardId` (uuid, FK -> Board.id, required)
  - `label` (string, required)
  - `metadata` (jsonb, nullable)
  - `positionX` (float, required)
  - `positionY` (float, required)
  - `createdAt` (timestamp, required)
  - `updatedAt` (timestamp, required)
- **Note**: Source of truth for rendering may remain scene JSON; this table is
  optional optimization for AI/queryability in MVP+.

## Entity: BoardConnection

- **Purpose**: Directed/undirected relationship between nodes.
- **Fields**:
  - `id` (uuid, PK)
  - `boardId` (uuid, FK -> Board.id, required)
  - `fromNodeId` (uuid, FK -> BoardNode.id, required)
  - `toNodeId` (uuid, FK -> BoardNode.id, required)
  - `metadata` (jsonb, nullable)
  - `createdAt` (timestamp, required)

## Entity: AssistantMessage

- **Purpose**: Chat history scoped to board context.
- **Fields**:
  - `id` (uuid, PK)
  - `boardId` (uuid, FK -> Board.id, required)
  - `userId` (uuid, FK -> User.id, required)
  - `role` (enum: `USER` | `ASSISTANT` | `SYSTEM`, required)
  - `content` (text, required)
  - `kind` (enum: `CHAT` | `GENERATE_NODES` | `SUMMARY`, required)
  - `status` (enum: `PENDING` | `COMPLETE` | `FAILED`, required)
  - `createdAt` (timestamp, required)

## Entity: GeneratedNodeProposal

- **Purpose**: Preview payload for confirm-before-insert flow.
- **Fields**:
  - `id` (uuid, PK)
  - `boardId` (uuid, FK -> Board.id, required)
  - `requestedByUserId` (uuid, FK -> User.id, required)
  - `proposalJson` (jsonb, required)
  - `expiresAt` (timestamp, required)
  - `acceptedAt` (timestamp, nullable)
  - `createdAt` (timestamp, required)

## State transitions

- **Board deletion**:
  - `ACTIVE` -> `SOFT_DELETED` (`isDeleted=true`, set `deletedAt` + `purgeAt`)
  - `SOFT_DELETED` -> `RESTORED` (within 30 days)
  - `SOFT_DELETED` -> `PURGED` (after purge job/manual cleanup)
- **Autosave conflict**:
  - client write against stale `version` -> write accepted by LWW, stale client
    receives warning signal and refresh prompt.
- **AI generation**:
  - `GENERATE_NODES` request -> `GeneratedNodeProposal`
  - user confirm -> nodes inserted
  - user cancel/expiry -> no board mutation
