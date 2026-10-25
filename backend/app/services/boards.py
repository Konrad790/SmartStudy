from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Board, User

RESTORE_WINDOW_DAYS = 30


def _assert_owner(board: Board, user: User) -> None:
    if board.ownerId != user.id:
        raise PermissionError("FORBIDDEN")


async def list_boards(db: AsyncSession, user: User) -> list[Board]:
    result = await db.execute(
        select(Board).where(Board.ownerId == user.id, Board.isDeleted.is_(False)).order_by(Board.updatedAt.desc())
    )
    return list(result.scalars().all())


async def create_board(db: AsyncSession, user: User, title: str) -> Board:
    board = Board(ownerId=user.id, title=title)
    db.add(board)
    await db.commit()
    await db.refresh(board)
    return board


async def get_board(db: AsyncSession, board_id: str) -> Board | None:
    result = await db.execute(select(Board).where(Board.id == board_id))
    return result.scalar_one_or_none()


async def delete_board(db: AsyncSession, user: User, board_id: str) -> Board:
    board = await get_board(db, board_id)
    if board is None:
        raise LookupError("NOT_FOUND")
    _assert_owner(board, user)
    now = datetime.now(timezone.utc)
    restore_until = now + timedelta(days=RESTORE_WINDOW_DAYS)
    board.isDeleted = True
    board.deletedAt = now
    board.purgeAt = restore_until
    await db.commit()
    await db.refresh(board)
    return board


async def restore_board(db: AsyncSession, user: User, board_id: str) -> Board:
    board = await get_board(db, board_id)
    if board is None:
        raise LookupError("NOT_FOUND")
    _assert_owner(board, user)
    board.isDeleted = False
    board.deletedAt = None
    board.purgeAt = None
    await db.commit()
    await db.refresh(board)
    return board


async def purge_expired_boards(db: AsyncSession, now: datetime | None = None) -> int:
    """Permanently delete soft-deleted boards whose restore window (`purgeAt`) has passed.

    Snapshots, assistant messages and proposals are removed by ON DELETE CASCADE.
    Returns the number of purged boards.
    """
    cutoff = now or datetime.now(timezone.utc)
    result = await db.execute(
        delete(Board).where(
            Board.isDeleted.is_(True),
            Board.purgeAt.is_not(None),
            Board.purgeAt <= cutoff,
        )
    )
    await db.commit()
    return result.rowcount or 0
