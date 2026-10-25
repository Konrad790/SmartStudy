from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import BoardListOut, BoardOut, CreateBoardIn, DeleteBoardOut
from app.services import boards as board_service

router = APIRouter(prefix="/boards", tags=["boards"])


@router.get("", response_model=BoardListOut)
async def list_boards(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await board_service.list_boards(db, user)
    return BoardListOut(items=[BoardOut.model_validate(b) for b in items])


@router.post("", response_model=BoardOut, status_code=201)
async def create_board(
    body: CreateBoardIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    board = await board_service.create_board(db, user, body.title.strip())
    return BoardOut.model_validate(board)


@router.delete("/{board_id}", response_model=DeleteBoardOut)
async def delete_board(
    board_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        board = await board_service.delete_board(db, user, board_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Not found") from None
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden") from None
    return DeleteBoardOut(deleted=board.isDeleted, restoreUntil=board.purgeAt)


@router.post("/{board_id}/restore", response_model=BoardOut)
async def restore_board(
    board_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        board = await board_service.restore_board(db, user, board_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Not found") from None
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden") from None
    return BoardOut.model_validate(board)
