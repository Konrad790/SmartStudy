# Data Model: SmartStudy Learning Boards Platform

## Entity: User

- **Purpose**: Account identity and ownership boundary for boards and questions.
- **Fields**:
  - `id` (uuid, PK)
  - `email` (string, unique, required)
  - `passwordHash` (string, required)
  - `displayName` (string, required)
  - `createdAt` (timestamp, required)
  - `updatedAt` (timestamp, required)
- **Validation rules**:
  - `email` must be valid email format.
  - `passwordHash` is never returned to client payloads.
- **Relationships**:
  - One-to-many with `Board`
  - One-to-many with `StudyQuestion`

## Entity: Session (logical/Auth.js-managed)

- **Purpose**: Authenticated access context.
- **Fields**:
  - `sessionToken` (string, unique)
  - `userId` (uuid, FK -> User.id)
  - `expiresAt` (timestamp)
- **Validation rules**:
  - Expired sessions cannot access board or assistant routes.

## Entity: Board

- **Purpose**: User-owned workspace listed on the dashboard.
- **Fields**:
  - `id` (uuid, PK)
  - `ownerId` (uuid, FK -> User.id, required)
  - `title` (string, required)
  - `subject` (enum: `MATH` | `PHYSICS`, required)
  - `isFavorite` (boolean, default false)
  - `lastOpenedAt` (timestamp, nullable)
  - `createdAt` (timestamp, required)
  - `updatedAt` (timestamp, required)
- **Validation rules**:
  - `title` min length 1, max length 120.
  - Subject constrained to enum values for initial release.
- **Relationships**:
  - One-to-many with `BoardSceneSnapshot`
  - One-to-many with `StudyQuestion`

## Entity: BoardSceneSnapshot

- **Purpose**: Persist Excalidraw scene state over time.
- **Fields**:
  - `id` (uuid, PK)
  - `boardId` (uuid, FK -> Board.id, required)
  - `sceneVersion` (int, required)
  - `elementsJson` (jsonb, required)
  - `appStateJson` (jsonb, required)
  - `filesJson` (jsonb, nullable)
  - `createdByUserId` (uuid, FK -> User.id, required)
  - `createdAt` (timestamp, required)
- **Validation rules**:
  - `elementsJson` must match expected Excalidraw scene array structure.
  - Snapshot writes require board ownership authorization.
- **Relationships**:
  - Many-to-one with `Board`

## Entity: StudyQuestion

- **Purpose**: Record user prompts and assistant answers in board context.
- **Fields**:
  - `id` (uuid, PK)
  - `boardId` (uuid, FK -> Board.id, required)
  - `userId` (uuid, FK -> User.id, required)
  - `questionText` (text, required)
  - `assistantAnswerText` (text, nullable on failure)
  - `status` (enum: `PENDING` | `ANSWERED` | `FAILED`, required)
  - `failureReason` (string, nullable)
  - `createdAt` (timestamp, required)
  - `answeredAt` (timestamp, nullable)
- **Validation rules**:
  - `questionText` min length 1, max length 4000.
  - Failed responses require `failureReason`.
- **Relationships**:
  - Many-to-one with `Board`
  - Many-to-one with `User`

## Entity: AssistantContextDigest

- **Purpose**: Cache summarized board context used for prompt grounding.
- **Fields**:
  - `boardId` (uuid, PK/FK -> Board.id)
  - `snapshotId` (uuid, FK -> BoardSceneSnapshot.id)
  - `digestText` (text, required)
  - `updatedAt` (timestamp, required)
- **Validation rules**:
  - Recomputed whenever a newer scene snapshot is saved.

## State transitions

- **Board lifecycle**:
  - `CREATED` -> `ACTIVE` (immediately after creation)
  - `ACTIVE` -> `ARCHIVED` (future extension, not in v1 contracts)
- **StudyQuestion lifecycle**:
  - `PENDING` -> `ANSWERED`
  - `PENDING` -> `FAILED`
  - no direct transition from `FAILED` to `ANSWERED`; retry creates new row.

## Indexing and constraints

- Unique index on `User.email`
- Indexes:
  - `Board.ownerId, Board.updatedAt DESC`
  - `Board.ownerId, Board.subject`
  - `Board.ownerId, Board.isFavorite`
  - `BoardSceneSnapshot.boardId, BoardSceneSnapshot.sceneVersion DESC`
  - `StudyQuestion.boardId, StudyQuestion.createdAt DESC`
