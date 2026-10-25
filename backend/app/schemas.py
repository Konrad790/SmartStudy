from datetime import datetime
from typing import Any

import base64
import re

from pydantic import BaseModel, Field, field_validator, model_validator


class ApiError(BaseModel):
    message: str
    code: str | None = None
    service: str | None = None


class BoardOut(BaseModel):
    id: str
    title: str
    isDeleted: bool
    purgeAt: datetime | None
    createdAt: datetime | None = None
    updatedAt: datetime | None = None

    model_config = {"from_attributes": True}


class BoardListOut(BaseModel):
    items: list[BoardOut]


class CreateBoardIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class DeleteBoardOut(BaseModel):
    deleted: bool
    restoreUntil: datetime | None


class SnapshotOut(BaseModel):
    id: str
    boardId: str
    version: int
    sceneJson: dict[str, Any]
    savedByUserId: str
    createdAt: datetime

    model_config = {"from_attributes": True}


class SnapshotPutIn(BaseModel):
    baseVersion: int = Field(ge=0)
    sceneJson: dict[str, Any]


class SnapshotPutOut(BaseModel):
    version: int
    staleWarning: bool


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversationId: str | None = None
    boardImageMimeType: str | None = None
    boardImageBase64: str | None = None
    patchBbox: dict[str, Any] | None = None
    visibleViewport: dict[str, Any] | None = None

    @field_validator("boardImageBase64")
    @classmethod
    def normalize_board_image_base64(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        match = re.match(r"^data:[^;]+;base64,(.+)$", trimmed, flags=re.IGNORECASE)
        payload = match.group(1) if match else trimmed
        return re.sub(r"\s+", "", payload)

    @field_validator("visibleViewport")
    @classmethod
    def validate_visible_viewport(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        required = ("minX", "minY", "maxX", "maxY", "zoom", "widthPx", "heightPx")
        missing = [key for key in required if key not in value]
        if missing:
            raise ValueError(f"visibleViewport missing fields: {', '.join(missing)}")
        for key in required:
            if not isinstance(value[key], (int, float)):
                raise ValueError(f"visibleViewport.{key} must be a number")
        if value["zoom"] <= 0 or value["widthPx"] <= 0 or value["heightPx"] <= 0:
            raise ValueError("visibleViewport zoom/widthPx/heightPx must be positive")
        if value["maxX"] < value["minX"] or value["maxY"] < value["minY"]:
            raise ValueError("visibleViewport bounds are invalid")
        return value

    @model_validator(mode="after")
    def validate_board_image_pair(self) -> "ChatIn":
        has_mime = bool(self.boardImageMimeType)
        has_b64 = bool(self.boardImageBase64)
        if has_mime != has_b64:
            raise ValueError("boardImageMimeType and boardImageBase64 must be sent together")
        if not has_b64:
            return self
        allowed = {"image/png", "image/jpeg", "image/webp"}
        if self.boardImageMimeType not in allowed:
            raise ValueError("Unsupported boardImageMimeType")
        try:
            raw = base64.b64decode(self.boardImageBase64, validate=True)
        except Exception as exc:
            raise ValueError("Invalid boardImageBase64") from exc
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError("Board image too large (max 4MB)")
        return self


class VisionSyncIn(BaseModel):
    boardImageMimeType: str
    boardImageBase64: str
    patchBbox: dict[str, Any] | None = None
    visibleViewport: dict[str, Any] | None = None

    @field_validator("boardImageBase64")
    @classmethod
    def normalize_board_image_base64(cls, value: str) -> str:
        trimmed = value.strip()
        match = re.match(r"^data:[^;]+;base64,(.+)$", trimmed, flags=re.IGNORECASE)
        payload = match.group(1) if match else trimmed
        return re.sub(r"\s+", "", payload)

    @field_validator("visibleViewport")
    @classmethod
    def validate_visible_viewport(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        required = ("minX", "minY", "maxX", "maxY", "zoom", "widthPx", "heightPx")
        missing = [key for key in required if key not in value]
        if missing:
            raise ValueError(f"visibleViewport missing fields: {', '.join(missing)}")
        for key in required:
            if not isinstance(value[key], (int, float)):
                raise ValueError(f"visibleViewport.{key} must be a number")
        if value["zoom"] <= 0 or value["widthPx"] <= 0 or value["heightPx"] <= 0:
            raise ValueError("visibleViewport zoom/widthPx/heightPx must be positive")
        if value["maxX"] < value["minX"] or value["maxY"] < value["minY"]:
            raise ValueError("visibleViewport bounds are invalid")
        return value

    @model_validator(mode="after")
    def validate_image_payload(self) -> "VisionSyncIn":
        allowed = {"image/png", "image/jpeg", "image/webp"}
        if self.boardImageMimeType not in allowed:
            raise ValueError("Unsupported boardImageMimeType")
        try:
            raw = base64.b64decode(self.boardImageBase64, validate=True)
        except Exception as exc:
            raise ValueError("Invalid boardImageBase64") from exc
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError("Board image too large (max 4MB)")
        return self


class VisionSyncOut(BaseModel):
    boardContextJson: dict[str, Any]
    status: str = "ok"


class ChatOut(BaseModel):
    message: str
    boardContextJson: dict[str, Any] | None = None
    todraw: dict[str, Any] | None = None
    conversationId: str | None = None


class ConversationOut(BaseModel):
    id: str
    boardId: str
    title: str
    createdAt: datetime
    updatedAt: datetime
    messageCount: int = 0
    lastMessagePreview: str | None = None


class ConversationCreateIn(BaseModel):
    title: str | None = None


class ConversationMessageOut(BaseModel):
    id: str
    conversationId: str | None = None
    role: str
    content: str
    createdAt: datetime


class DrawIn(BaseModel):
    todraw: dict[str, Any]
    visibleViewport: dict[str, Any] | None = None
    boardContextJson: dict[str, Any] | None = None
    existingElementBboxes: list[dict[str, Any]] | None = None

    @field_validator("visibleViewport")
    @classmethod
    def validate_draw_viewport(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        required = ("minX", "minY", "maxX", "maxY", "zoom", "widthPx", "heightPx")
        missing = [key for key in required if key not in value]
        if missing:
            raise ValueError(f"visibleViewport missing fields: {', '.join(missing)}")
        for key in required:
            if not isinstance(value[key], (int, float)):
                raise ValueError(f"visibleViewport.{key} must be a number")
        if value["zoom"] <= 0 or value["widthPx"] <= 0 or value["heightPx"] <= 0:
            raise ValueError("visibleViewport zoom/widthPx/heightPx must be positive")
        if value["maxX"] < value["minX"] or value["maxY"] < value["minY"]:
            raise ValueError("visibleViewport bounds are invalid")
        return value


class DrawOut(BaseModel):
    elements: list[dict[str, Any]]
    notes: str | None = None
