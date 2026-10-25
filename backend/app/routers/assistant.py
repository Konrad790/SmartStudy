from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.ratelimit import ai_rate_limit
from app.schemas import (
    ChatIn,
    ChatOut,
    ConversationCreateIn,
    ConversationMessageOut,
    ConversationOut,
    DrawIn,
    DrawOut,
    VisionSyncIn,
    VisionSyncOut,
)
from app.services import assistant as assistant_service
from app.services.gemini import AIServiceError

router = APIRouter(
    prefix="/boards/{board_id}/assistant",
    tags=["assistant"],
    dependencies=[Depends(ai_rate_limit)],
)


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    board_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await assistant_service.list_board_conversations(db, board_id, user.id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Board not found") from None
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden") from None


@router.post("/conversations", response_model=ConversationOut)
async def create_conversation(
    board_id: str,
    body: ConversationCreateIn | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        title = body.title if body else None
        conv = await assistant_service.create_board_conversation(db, board_id, user.id, title=title)
        return ConversationOut(
            id=conv.id,
            boardId=conv.boardId,
            title=conv.title,
            createdAt=conv.createdAt,
            updatedAt=conv.updatedAt,
            messageCount=0,
            lastMessagePreview=None,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Board not found") from None
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden") from None


@router.get("/conversations/{conversation_id}/messages", response_model=list[ConversationMessageOut])
async def get_conversation_messages(
    board_id: str,
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await assistant_service.get_conversation_messages(db, board_id, user.id, conversation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden") from None


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    board_id: str,
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await assistant_service.delete_board_conversation(db, board_id, user.id, conversation_id)
        return {"status": "ok"}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden") from None


@router.post("/vision-sync", response_model=VisionSyncOut)
async def vision_sync(
    board_id: str,
    body: VisionSyncIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        context = await assistant_service.sync_board_vision(
            db,
            user,
            board_id,
            image_mime=body.boardImageMimeType,
            image_b64=body.boardImageBase64,
            patch_bbox=body.patchBbox,
            visible_viewport=body.visibleViewport,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Not found") from None
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden") from None
    except AIServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail={"message": exc.message, "service": f"{exc.service} ({exc.model})", "code": "AI_ERROR"},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": str(exc), "service": "assistant/vision-sync", "code": "VALIDATION_ERROR"},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"message": str(exc), "service": "assistant/vision-sync", "code": "INTERNAL_ERROR"},
        ) from exc
    return VisionSyncOut(boardContextJson=context)


@router.post("/chat", response_model=ChatOut)
async def chat(
    board_id: str,
    body: ChatIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        reply, board_context, todraw, conv_id = await assistant_service.chat_on_board(
            db,
            user,
            board_id,
            body.message.strip(),
            conversation_id=body.conversationId,
            board_image_mime=body.boardImageMimeType,
            board_image_b64=body.boardImageBase64,
            visible_viewport=body.visibleViewport,
            patch_bbox=body.patchBbox,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Not found") from None
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden") from None
    except AIServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail={"message": exc.message, "service": f"{exc.service} ({exc.model})", "code": "AI_ERROR"},
        ) from exc
    except ValueError as exc:
        msg = str(exc)
        if msg == "BOARD_IMAGE_REQUIRED":
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Board screenshot is required. Draw on the board or refresh and try again.",
                    "service": "assistant/chat",
                    "code": "IMAGE_REQUIRED",
                },
            ) from exc
        raise HTTPException(
            status_code=400,
            detail={"message": msg, "service": "assistant/chat", "code": "VALIDATION_ERROR"},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"message": str(exc), "service": "assistant/chat", "code": "INTERNAL_ERROR"},
        ) from exc
    return ChatOut(message=reply, boardContextJson=board_context, todraw=todraw, conversationId=conv_id)


@router.post("/chat/stream")
async def chat_stream(
    board_id: str,
    body: ChatIn,
    user: User = Depends(get_current_user),
):
    stream = assistant_service.chat_stream_on_board(
        user,
        board_id,
        body.message.strip(),
        conversation_id=body.conversationId,
        board_image_mime=body.boardImageMimeType,
        board_image_b64=body.boardImageBase64,
        visible_viewport=body.visibleViewport,
        patch_bbox=body.patchBbox,
    )
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/draw", response_model=DrawOut)
async def draw(
    board_id: str,
    body: DrawIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        elements, notes = await assistant_service.draw_on_board(
            db,
            user,
            board_id,
            todraw=body.todraw,
            visible_viewport=body.visibleViewport,
            board_context=body.boardContextJson,
            existing_element_bboxes=body.existingElementBboxes,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Not found") from None
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden") from None
    except AIServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail={"message": exc.message, "service": f"{exc.service} ({exc.model})", "code": "AI_ERROR"},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": str(exc), "service": "assistant/draw", "code": "VALIDATION_ERROR"},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"message": str(exc), "service": "assistant/draw", "code": "INTERNAL_ERROR"},
        ) from exc
    return DrawOut(elements=elements, notes=notes)
