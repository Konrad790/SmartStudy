from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import SnapshotOut, SnapshotPutIn, SnapshotPutOut
from app.services import boards as board_service
from app.services import snapshots as snapshot_service

router = APIRouter(prefix="/boards/{board_id}/snapshot", tags=["snapshots"])


async def _assert_board_access(db: AsyncSession, user: User, board_id: str) -> None:
    board = await board_service.get_board(db, board_id)
    if board is None:
        raise HTTPException(status_code=404, detail="Not found")
    if board.ownerId != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("", response_model=SnapshotOut)
async def get_snapshot(
    board_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _assert_board_access(db, user, board_id)
    snapshot = await snapshot_service.load_latest(db, board_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Not found")
    return SnapshotOut.model_validate(snapshot)


@router.put("", response_model=SnapshotPutOut)
async def put_snapshot(
    board_id: str,
    body: SnapshotPutIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        version, stale = await snapshot_service.save_snapshot(
            db, user, board_id, body.baseVersion, body.sceneJson
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Not found") from None
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden") from None
    return SnapshotPutOut(version=version, staleWarning=stale)
