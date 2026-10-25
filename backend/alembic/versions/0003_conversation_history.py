"""Add BoardConversation and AssistantMessage.conversationId.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-25

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS "BoardConversation" (
            "id" TEXT NOT NULL,
            "boardId" TEXT NOT NULL,
            "userId" TEXT NOT NULL,
            "title" TEXT NOT NULL DEFAULT 'Nowa konwersacja',
            "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT "BoardConversation_pkey" PRIMARY KEY ("id")
        )
        """
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS "BoardConversation_boardId_updatedAt_idx" ON "BoardConversation"("boardId", "updatedAt" DESC)'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS "BoardConversation_userId_idx" ON "BoardConversation"("userId")'
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'BoardConversation_boardId_fkey'
            ) THEN
                ALTER TABLE "BoardConversation"
                ADD CONSTRAINT "BoardConversation_boardId_fkey"
                FOREIGN KEY ("boardId") REFERENCES "Board"("id") ON DELETE CASCADE ON UPDATE CASCADE;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'BoardConversation_userId_fkey'
            ) THEN
                ALTER TABLE "BoardConversation"
                ADD CONSTRAINT "BoardConversation_userId_fkey"
                FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        ALTER TABLE "AssistantMessage"
        ADD COLUMN IF NOT EXISTS "conversationId" TEXT;
        """
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS "AssistantMessage_conversationId_createdAt_idx" ON "AssistantMessage"("conversationId", "createdAt")'
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'AssistantMessage_conversationId_fkey'
            ) THEN
                ALTER TABLE "AssistantMessage"
                ADD CONSTRAINT "AssistantMessage_conversationId_fkey"
                FOREIGN KEY ("conversationId") REFERENCES "BoardConversation"("id") ON DELETE CASCADE ON UPDATE CASCADE;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        'ALTER TABLE "AssistantMessage" DROP CONSTRAINT IF EXISTS "AssistantMessage_conversationId_fkey"'
    )
    op.execute(
        'DROP INDEX IF EXISTS "AssistantMessage_conversationId_createdAt_idx"'
    )
    op.execute(
        'ALTER TABLE "AssistantMessage" DROP COLUMN IF EXISTS "conversationId"'
    )
    op.execute('DROP TABLE IF EXISTS "BoardConversation" CASCADE')
