"""Initial schema (replaces former Prisma migrations).

Revision ID: 0001
Revises:
Create Date: 2026-05-16

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE "User" (
            "id" TEXT NOT NULL,
            "email" TEXT NOT NULL,
            "passwordHash" TEXT NOT NULL DEFAULT '',
            "clerkId" TEXT,
            "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT "User_pkey" PRIMARY KEY ("id")
        )
        """
    )
    op.execute('CREATE UNIQUE INDEX "User_email_key" ON "User"("email")')
    op.execute('CREATE UNIQUE INDEX "User_clerkId_key" ON "User"("clerkId")')

    op.execute(
        """
        CREATE TABLE "Board" (
            "id" TEXT NOT NULL,
            "ownerId" TEXT NOT NULL,
            "title" TEXT NOT NULL,
            "isDeleted" BOOLEAN NOT NULL DEFAULT false,
            "deletedAt" TIMESTAMP(3),
            "purgeAt" TIMESTAMP(3),
            "lastOpenedAt" TIMESTAMP(3),
            "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT "Board_pkey" PRIMARY KEY ("id")
        )
        """
    )
    op.execute('CREATE INDEX "Board_ownerId_updatedAt_idx" ON "Board"("ownerId", "updatedAt")')
    op.execute(
        """
        ALTER TABLE "Board"
        ADD CONSTRAINT "Board_ownerId_fkey"
        FOREIGN KEY ("ownerId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE
        """
    )

    op.execute(
        """
        CREATE TABLE "BoardSnapshot" (
            "id" TEXT NOT NULL,
            "boardId" TEXT NOT NULL,
            "version" INTEGER NOT NULL,
            "sceneJson" JSONB NOT NULL,
            "savedByUserId" TEXT NOT NULL,
            "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT "BoardSnapshot_pkey" PRIMARY KEY ("id")
        )
        """
    )
    op.execute(
        'CREATE INDEX "BoardSnapshot_boardId_version_idx" ON "BoardSnapshot"("boardId", "version")'
    )
    op.execute(
        """
        ALTER TABLE "BoardSnapshot"
        ADD CONSTRAINT "BoardSnapshot_boardId_fkey"
        FOREIGN KEY ("boardId") REFERENCES "Board"("id") ON DELETE CASCADE ON UPDATE CASCADE
        """
    )

    op.execute(
        """
        CREATE TABLE "AssistantMessage" (
            "id" TEXT NOT NULL,
            "boardId" TEXT NOT NULL,
            "userId" TEXT NOT NULL,
            "role" TEXT NOT NULL,
            "kind" TEXT NOT NULL,
            "status" TEXT NOT NULL,
            "content" TEXT NOT NULL,
            "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT "AssistantMessage_pkey" PRIMARY KEY ("id")
        )
        """
    )
    op.execute(
        'CREATE INDEX "AssistantMessage_boardId_createdAt_idx" ON "AssistantMessage"("boardId", "createdAt")'
    )
    op.execute(
        """
        ALTER TABLE "AssistantMessage"
        ADD CONSTRAINT "AssistantMessage_boardId_fkey"
        FOREIGN KEY ("boardId") REFERENCES "Board"("id") ON DELETE CASCADE ON UPDATE CASCADE
        """
    )
    op.execute(
        """
        ALTER TABLE "AssistantMessage"
        ADD CONSTRAINT "AssistantMessage_userId_fkey"
        FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE
        """
    )

    op.execute(
        """
        CREATE TABLE "GeneratedNodeProposal" (
            "id" TEXT NOT NULL,
            "boardId" TEXT NOT NULL,
            "requestedByUserId" TEXT NOT NULL,
            "proposalJson" JSONB NOT NULL,
            "expiresAt" TIMESTAMP(3) NOT NULL,
            "acceptedAt" TIMESTAMP(3),
            "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT "GeneratedNodeProposal_pkey" PRIMARY KEY ("id")
        )
        """
    )
    op.execute(
        """
        ALTER TABLE "GeneratedNodeProposal"
        ADD CONSTRAINT "GeneratedNodeProposal_boardId_fkey"
        FOREIGN KEY ("boardId") REFERENCES "Board"("id") ON DELETE CASCADE ON UPDATE CASCADE
        """
    )
    op.execute(
        """
        ALTER TABLE "GeneratedNodeProposal"
        ADD CONSTRAINT "GeneratedNodeProposal_requestedByUserId_fkey"
        FOREIGN KEY ("requestedByUserId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE
        """
    )


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS "GeneratedNodeProposal" CASCADE')
    op.execute('DROP TABLE IF EXISTS "AssistantMessage" CASCADE')
    op.execute('DROP TABLE IF EXISTS "BoardSnapshot" CASCADE')
    op.execute('DROP TABLE IF EXISTS "Board" CASCADE')
    op.execute('DROP TABLE IF EXISTS "User" CASCADE')
