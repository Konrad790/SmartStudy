import json
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.models import AssistantMessage, BoardConversation, User
from app.schemas import ConversationMessageOut, ConversationOut
from app.services.boards import get_board
from app.services.gemini import (
    AIServiceError,
    ConversationMessage,
    PipelineResult,
    draw_agent,
    run_pipeline,
    run_pipeline_stream,
    vision_parser_agent,
    vision_patch_agent,
)


def _format_conversation_title(message: str) -> str:
    cleaned = " ".join(message.split())
    if not cleaned:
        return "Nowa konwersacja"
    return cleaned[:36] + ("…" if len(cleaned) > 36 else "")


async def get_or_create_conversation(
    db: AsyncSession,
    board_id: str,
    user_id: str,
    conversation_id: str | None = None,
    title: str | None = None,
) -> BoardConversation:
    if conversation_id:
        conv = await db.get(BoardConversation, conversation_id)
        if conv and conv.boardId == board_id and conv.userId == user_id:
            return conv
        raise LookupError("CONVERSATION_NOT_FOUND")

    conv_title = _format_conversation_title(title) if title else "Nowa konwersacja"
    conv = BoardConversation(
        boardId=board_id,
        userId=user_id,
        title=conv_title,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def list_board_conversations(
    db: AsyncSession,
    board_id: str,
    user_id: str,
) -> list[ConversationOut]:
    board = await get_board(db, board_id)
    if board is None:
        raise LookupError("NOT_FOUND")
    if board.ownerId != user_id:
        raise PermissionError("FORBIDDEN")

    # Migrate any legacy unattached messages
    legacy_count = await db.scalar(
        select(func.count(AssistantMessage.id)).where(
            AssistantMessage.boardId == board_id,
            AssistantMessage.userId == user_id,
            AssistantMessage.conversationId.is_(None),
            AssistantMessage.kind == "CHAT",
        )
    )
    if legacy_count and legacy_count > 0:
        first_legacy_msg = await db.scalar(
            select(AssistantMessage.content)
            .where(
                AssistantMessage.boardId == board_id,
                AssistantMessage.userId == user_id,
                AssistantMessage.conversationId.is_(None),
                AssistantMessage.kind == "CHAT",
            )
            .order_by(AssistantMessage.createdAt.asc())
            .limit(1)
        )
        legacy_title = _format_conversation_title(first_legacy_msg or "Poprzednia rozmowa")
        legacy_conv = BoardConversation(
            boardId=board_id,
            userId=user_id,
            title=legacy_title,
        )
        db.add(legacy_conv)
        await db.flush()
        await db.execute(
            update(AssistantMessage)
            .where(
                AssistantMessage.boardId == board_id,
                AssistantMessage.userId == user_id,
                AssistantMessage.conversationId.is_(None),
                AssistantMessage.kind == "CHAT",
            )
            .values(conversationId=legacy_conv.id)
        )
        await db.commit()

    result = await db.execute(
        select(BoardConversation)
        .where(
            BoardConversation.boardId == board_id,
            BoardConversation.userId == user_id,
        )
        .order_by(BoardConversation.updatedAt.desc())
    )
    conversations = result.scalars().all()

    items: list[ConversationOut] = []
    for conv in conversations:
        msg_count = (
            await db.scalar(
                select(func.count(AssistantMessage.id)).where(
                    AssistantMessage.conversationId == conv.id,
                    AssistantMessage.kind == "CHAT",
                )
            )
            or 0
        )
        last_msg = await db.scalar(
            select(AssistantMessage.content)
            .where(
                AssistantMessage.conversationId == conv.id,
                AssistantMessage.kind == "CHAT",
            )
            .order_by(AssistantMessage.createdAt.desc())
            .limit(1)
        )
        preview = (last_msg[:60] + "…") if last_msg and len(last_msg) > 60 else last_msg
        items.append(
            ConversationOut(
                id=conv.id,
                boardId=conv.boardId,
                title=conv.title,
                createdAt=conv.createdAt,
                updatedAt=conv.updatedAt,
                messageCount=msg_count,
                lastMessagePreview=preview,
            )
        )
    return items


async def create_board_conversation(
    db: AsyncSession,
    board_id: str,
    user_id: str,
    title: str | None = None,
) -> BoardConversation:
    board = await get_board(db, board_id)
    if board is None:
        raise LookupError("NOT_FOUND")
    if board.ownerId != user_id:
        raise PermissionError("FORBIDDEN")

    conv_title = _format_conversation_title(title) if title else "Nowa konwersacja"
    conv = BoardConversation(
        boardId=board_id,
        userId=user_id,
        title=conv_title,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def get_conversation_messages(
    db: AsyncSession,
    board_id: str,
    user_id: str,
    conversation_id: str,
) -> list[ConversationMessageOut]:
    board = await get_board(db, board_id)
    if board is None:
        raise LookupError("NOT_FOUND")
    if board.ownerId != user_id:
        raise PermissionError("FORBIDDEN")

    conv = await db.get(BoardConversation, conversation_id)
    if not conv or conv.boardId != board_id or conv.userId != user_id:
        raise LookupError("CONVERSATION_NOT_FOUND")

    result = await db.execute(
        select(AssistantMessage)
        .where(
            AssistantMessage.conversationId == conversation_id,
            AssistantMessage.kind == "CHAT",
        )
        .order_by(AssistantMessage.createdAt.asc())
    )
    messages = result.scalars().all()
    return [
        ConversationMessageOut(
            id=m.id,
            conversationId=m.conversationId,
            role="user" if m.role == "USER" else "assistant",
            content=m.content,
            createdAt=m.createdAt,
        )
        for m in messages
    ]


async def delete_board_conversation(
    db: AsyncSession,
    board_id: str,
    user_id: str,
    conversation_id: str,
) -> None:
    board = await get_board(db, board_id)
    if board is None:
        raise LookupError("NOT_FOUND")
    if board.ownerId != user_id:
        raise PermissionError("FORBIDDEN")

    conv = await db.get(BoardConversation, conversation_id)
    if not conv or conv.boardId != board_id or conv.userId != user_id:
        raise LookupError("CONVERSATION_NOT_FOUND")

    await db.delete(conv)
    await db.commit()


async def _load_conversation_history(
    db: AsyncSession,
    board_id: str,
    user_id: str,
    conversation_id: str | None = None,
) -> list[ConversationMessage]:
    if not conversation_id:
        return []

    result = await db.execute(
        select(AssistantMessage)
        .where(
            AssistantMessage.boardId == board_id,
            AssistantMessage.userId == user_id,
            AssistantMessage.conversationId == conversation_id,
            AssistantMessage.kind == "CHAT",
        )
        .order_by(AssistantMessage.createdAt.asc())
    )
    history: list[ConversationMessage] = []
    for row in result.scalars().all():
        role = "user" if row.role == "USER" else "assistant"
        history.append(ConversationMessage(role=role, content=row.content))
    return history


async def get_latest_board_context(
    db: AsyncSession,
    board_id: str,
    user_id: str,
) -> dict[str, Any] | None:
    result = await db.execute(
        select(AssistantMessage)
        .where(
            AssistantMessage.boardId == board_id,
            AssistantMessage.userId == user_id,
            AssistantMessage.kind == "BOARD_CONTEXT",
        )
        .order_by(AssistantMessage.createdAt.desc())
        .limit(1)
    )
    msg = result.scalars().first()
    if msg and msg.content:
        try:
            parsed = json.loads(msg.content)
            if isinstance(parsed, dict) and not parsed.get("error"):
                return parsed
        except Exception:
            return None
    return None


async def save_board_context(
    db: AsyncSession,
    board_id: str,
    user_id: str,
    board_context: dict[str, Any],
) -> None:
    db.add(
        AssistantMessage(
            boardId=board_id,
            userId=user_id,
            role="ASSISTANT",
            kind="BOARD_CONTEXT",
            status="COMPLETE",
            content=json.dumps(board_context, ensure_ascii=False),
        )
    )
    await db.commit()


async def sync_board_vision(
    db: AsyncSession,
    user: User,
    board_id: str,
    *,
    image_mime: str,
    image_b64: str,
    patch_bbox: dict | None = None,
    visible_viewport: dict | None = None,
) -> dict[str, Any]:
    board = await get_board(db, board_id)
    if board is None:
        raise LookupError("NOT_FOUND")
    if board.ownerId != user.id:
        raise PermissionError("FORBIDDEN")

    existing_context = await get_latest_board_context(db, board_id, user.id)

    if patch_bbox and existing_context:
        updated_context = await vision_patch_agent(
            image_mime=image_mime,
            image_b64=image_b64,
            patch_bbox=patch_bbox,
            existing_context=existing_context,
        )
    else:
        updated_context = await vision_parser_agent(
            image_mime=image_mime,
            image_b64=image_b64,
            existing_context=existing_context,
        )

    await save_board_context(db, board_id, user.id, updated_context)
    return updated_context


async def chat_on_board(
    db: AsyncSession,
    user: User,
    board_id: str,
    message: str,
    *,
    conversation_id: str | None = None,
    board_image_mime: str | None = None,
    board_image_b64: str | None = None,
    visible_viewport: dict | None = None,
    patch_bbox: dict | None = None,
) -> tuple[str, dict | None, dict | None, str]:
    board = await get_board(db, board_id)
    if board is None:
        raise LookupError("NOT_FOUND")
    if board.ownerId != user.id:
        raise PermissionError("FORBIDDEN")

    conv = await get_or_create_conversation(
        db, board_id, user.id, conversation_id=conversation_id, title=message
    )

    history = await _load_conversation_history(db, board_id, user.id, conversation_id=conv.id)
    existing_context = await get_latest_board_context(db, board_id, user.id)

    pipeline = await run_pipeline(
        user_message=message,
        history=history,
        image_mime=board_image_mime,
        image_b64=board_image_b64,
        visible_viewport=visible_viewport,
        patch_bbox=patch_bbox,
        existing_board_context=existing_context,
    )

    now = datetime.now(timezone.utc)
    db.add(
        AssistantMessage(
            boardId=board_id,
            userId=user.id,
            conversationId=conv.id,
            role="USER",
            kind="CHAT",
            status="COMPLETE",
            content=message,
        )
    )
    await db.flush()

    if pipeline.board_context is not None and not pipeline.board_context.get("error"):
        db.add(
            AssistantMessage(
                boardId=board_id,
                userId=user.id,
                role="ASSISTANT",
                kind="BOARD_CONTEXT",
                status="COMPLETE",
                content=json.dumps(pipeline.board_context, ensure_ascii=False),
            )
        )

    db.add(
        AssistantMessage(
            boardId=board_id,
            userId=user.id,
            conversationId=conv.id,
            role="ASSISTANT",
            kind="CHAT",
            status="COMPLETE",
            content=pipeline.reply,
        )
    )
    conv.updatedAt = now
    if conv.title in ("Nowa konwersacja", "New conversation"):
        conv.title = _format_conversation_title(message)
    await db.commit()
    return pipeline.reply, pipeline.board_context, pipeline.todraw, conv.id


async def chat_stream_on_board(
    user: User,
    board_id: str,
    message: str,
    *,
    conversation_id: str | None = None,
    board_image_mime: str | None = None,
    board_image_b64: str | None = None,
    visible_viewport: dict | None = None,
    patch_bbox: dict | None = None,
) -> AsyncGenerator[str, None]:
    async with SessionLocal() as db:
        board = await get_board(db, board_id)
        if board is None:
            yield f"data: {json.dumps({'type': 'error', 'error': 'Board not found'}, ensure_ascii=False)}\n\n"
            return
        if board.ownerId != user.id:
            yield f"data: {json.dumps({'type': 'error', 'error': 'Forbidden'}, ensure_ascii=False)}\n\n"
            return

        try:
            conv = await get_or_create_conversation(
                db, board_id, user.id, conversation_id=conversation_id, title=message
            )
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)}, ensure_ascii=False)}\n\n"
            return

        history = await _load_conversation_history(db, board_id, user.id, conversation_id=conv.id)
        existing_context = await get_latest_board_context(db, board_id, user.id)

        # Save user message immediately to the conversation
        now = datetime.now(timezone.utc)
        db.add(
            AssistantMessage(
                boardId=board_id,
                userId=user.id,
                conversationId=conv.id,
                role="USER",
                kind="CHAT",
                status="COMPLETE",
                content=message,
            )
        )
        conv.updatedAt = now
        if conv.title in ("Nowa konwersacja", "New conversation"):
            conv.title = _format_conversation_title(message)
        await db.commit()

        try:
            pipeline_result: PipelineResult | None = None
            async for kind, payload in run_pipeline_stream(
                user_message=message,
                history=history,
                image_mime=board_image_mime,
                image_b64=board_image_b64,
                visible_viewport=visible_viewport,
                patch_bbox=patch_bbox,
                existing_board_context=existing_context,
            ):
                if kind == "status":
                    yield f"data: {json.dumps({'type': 'status', **payload}, ensure_ascii=False)}\n\n"
                elif kind == "delta":
                    yield f"data: {json.dumps({'type': 'delta', 'text': payload}, ensure_ascii=False)}\n\n"
                elif kind == "done":
                    pipeline_result = payload

            if pipeline_result is not None:
                if pipeline_result.board_context is not None and not pipeline_result.board_context.get("error"):
                    db.add(
                        AssistantMessage(
                            boardId=board_id,
                            userId=user.id,
                            role="ASSISTANT",
                            kind="BOARD_CONTEXT",
                            status="COMPLETE",
                            content=json.dumps(pipeline_result.board_context, ensure_ascii=False),
                        )
                    )

                db.add(
                    AssistantMessage(
                        boardId=board_id,
                        userId=user.id,
                        conversationId=conv.id,
                        role="ASSISTANT",
                        kind="CHAT",
                        status="COMPLETE",
                        content=pipeline_result.reply,
                    )
                )
                conv.updatedAt = datetime.now(timezone.utc)
                await db.commit()

                done_payload = {
                    "type": "done",
                    "message": pipeline_result.reply,
                    "boardContextJson": pipeline_result.board_context,
                    "todraw": pipeline_result.todraw,
                    "conversationId": conv.id,
                }
                yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
        except AIServiceError as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc), 'service': exc.service, 'model': exc.model}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': f'[Assistant Service] {exc}', 'service': 'Assistant Service'}, ensure_ascii=False)}\n\n"


async def draw_on_board(
    db: AsyncSession,
    user: User,
    board_id: str,
    *,
    todraw: dict,
    visible_viewport: dict | None = None,
    board_context: dict | None = None,
    existing_element_bboxes: list[dict] | None = None,
) -> tuple[list[dict], str | None]:
    board = await get_board(db, board_id)
    if board is None:
        raise LookupError("NOT_FOUND")
    if board.ownerId != user.id:
        raise PermissionError("FORBIDDEN")

    elements, notes = await draw_agent(
        todraw=todraw,
        visible_viewport=visible_viewport,
        board_context=board_context,
        existing_element_bboxes=existing_element_bboxes,
    )
    return elements, notes
