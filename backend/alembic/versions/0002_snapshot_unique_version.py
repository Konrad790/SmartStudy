"""Enforce unique (boardId, version) on BoardSnapshot.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-24

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove accidental duplicates (possible before this constraint existed), keep the newest row.
    op.execute(
        """
        DELETE FROM "BoardSnapshot" a
        USING "BoardSnapshot" b
        WHERE a."boardId" = b."boardId"
          AND a."version" = b."version"
          AND (a."createdAt", a."id") < (b."createdAt", b."id")
        """
    )
    op.execute('DROP INDEX IF EXISTS "BoardSnapshot_boardId_version_idx"')
    op.execute(
        'ALTER TABLE "BoardSnapshot" '
        'ADD CONSTRAINT "BoardSnapshot_boardId_version_key" UNIQUE ("boardId", "version")'
    )


def downgrade() -> None:
    op.execute('ALTER TABLE "BoardSnapshot" DROP CONSTRAINT IF EXISTS "BoardSnapshot_boardId_version_key"')
    op.execute(
        'CREATE INDEX "BoardSnapshot_boardId_version_idx" ON "BoardSnapshot"("boardId", "version")'
    )
