from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import BoardSnapshot, User
from app.services.boards import get_board

_MAX_VERSION_ATTEMPTS = 5


async def load_latest(db: AsyncSession, board_id: str) -> BoardSnapshot | None:
    result = await db.execute(
        select(BoardSnapshot).where(BoardSnapshot.boardId == board_id).order_by(BoardSnapshot.version.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def save_snapshot(
    db: AsyncSession,
    user: User,
    board_id: str,
    base_version: int,
    scene_json: dict,
) -> tuple[int, bool]:
    board = await get_board(db, board_id)
    if board is None:
        raise LookupError("NOT_FOUND")
    if board.ownerId != user.id:
        raise PermissionError("FORBIDDEN")

    # Read the id once: after a rollback ORM instances are expired and lazy refresh is unavailable in async.
    user_id = user.id

    # Optimistic concurrency: `UNIQUE (boardId, version)` rejects two writers that computed the same
    # next version, the loser re-reads the latest version and retries.
    for attempt in range(_MAX_VERSION_ATTEMPTS):
        latest = await load_latest(db, board_id)
        latest_version = latest.version if latest else 0
        # The client's base is stale if anyone saved after it (re-evaluated on every retry).
        stale_warning = base_version > 0 and base_version < latest_version
        version = latest_version + 1

        db.add(
            BoardSnapshot(
                boardId=board_id,
                version=version,
                sceneJson=scene_json,
                savedByUserId=user_id,
            )
        )
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            if attempt == _MAX_VERSION_ATTEMPTS - 1:
                raise
            continue

        await _prune_old_snapshots(db, board_id, version)
        return version, stale_warning

    raise RuntimeError("unreachable")  # pragma: no cover


async def _prune_old_snapshots(db: AsyncSession, board_id: str, newest_version: int) -> None:
    """Keep only the newest `settings.snapshot_retention` versions of a board."""
    keep = max(1, settings.snapshot_retention)
    cutoff = newest_version - keep
    if cutoff <= 0:
        return
    await db.execute(
        delete(BoardSnapshot).where(
            BoardSnapshot.boardId == board_id,
            BoardSnapshot.version <= cutoff,
        )
    )
    await db.commit()
