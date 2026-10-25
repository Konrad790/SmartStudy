import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "User"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    passwordHash: Mapped[str] = mapped_column("passwordHash", String, nullable=False, default="")
    clerkId: Mapped[str | None] = mapped_column("clerkId", String, unique=True, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), default=_utc_now, server_default=func.now()
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
        server_default=func.now(),
    )

    boards: Mapped[list["Board"]] = relationship(back_populates="owner")
    conversations: Mapped[list["BoardConversation"]] = relationship(back_populates="user")
    generatedProposals: Mapped[list["GeneratedNodeProposal"]] = relationship(back_populates="requestedBy")


class Board(Base):
    __tablename__ = "Board"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ownerId: Mapped[str] = mapped_column("ownerId", String, ForeignKey("User.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    isDeleted: Mapped[bool] = mapped_column("isDeleted", Boolean, default=False)
    deletedAt: Mapped[datetime | None] = mapped_column("deletedAt", DateTime(timezone=True), nullable=True)
    purgeAt: Mapped[datetime | None] = mapped_column("purgeAt", DateTime(timezone=True), nullable=True)
    lastOpenedAt: Mapped[datetime | None] = mapped_column("lastOpenedAt", DateTime(timezone=True), nullable=True)
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), default=_utc_now, server_default=func.now()
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
        server_default=func.now(),
    )

    owner: Mapped["User"] = relationship(back_populates="boards")
    snapshots: Mapped[list["BoardSnapshot"]] = relationship(back_populates="board")
    conversations: Mapped[list["BoardConversation"]] = relationship(
        back_populates="board", cascade="all, delete-orphan"
    )
    generatedProposals: Mapped[list["GeneratedNodeProposal"]] = relationship(back_populates="board")

    __table_args__ = (Index("Board_ownerId_updatedAt_idx", "ownerId", "updatedAt"),)


class BoardSnapshot(Base):
    __tablename__ = "BoardSnapshot"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    boardId: Mapped[str] = mapped_column("boardId", String, ForeignKey("Board.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    sceneJson: Mapped[dict] = mapped_column("sceneJson", JSONB, nullable=False)
    savedByUserId: Mapped[str] = mapped_column("savedByUserId", String, nullable=False)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())

    board: Mapped["Board"] = relationship(back_populates="snapshots")

    __table_args__ = (UniqueConstraint("boardId", "version", name="BoardSnapshot_boardId_version_key"),)


class BoardConversation(Base):
    __tablename__ = "BoardConversation"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    boardId: Mapped[str] = mapped_column("boardId", String, ForeignKey("Board.id", ondelete="CASCADE"))
    userId: Mapped[str] = mapped_column("userId", String, ForeignKey("User.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String, nullable=False, default="Nowa konwersacja")
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), default=_utc_now, server_default=func.now()
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
        server_default=func.now(),
    )

    board: Mapped["Board"] = relationship(back_populates="conversations")
    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["AssistantMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("BoardConversation_boardId_updatedAt_idx", "boardId", "updatedAt"),
        Index("BoardConversation_userId_idx", "userId"),
    )


class AssistantMessage(Base):
    __tablename__ = "AssistantMessage"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    boardId: Mapped[str] = mapped_column("boardId", String, ForeignKey("Board.id", ondelete="CASCADE"))
    userId: Mapped[str] = mapped_column("userId", String, ForeignKey("User.id", ondelete="CASCADE"))
    conversationId: Mapped[str | None] = mapped_column(
        "conversationId", String, ForeignKey("BoardConversation.id", ondelete="CASCADE"), nullable=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["BoardConversation | None"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("AssistantMessage_boardId_createdAt_idx", "boardId", "createdAt"),
        Index("AssistantMessage_conversationId_createdAt_idx", "conversationId", "createdAt"),
    )


class GeneratedNodeProposal(Base):
    __tablename__ = "GeneratedNodeProposal"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    boardId: Mapped[str] = mapped_column("boardId", String, ForeignKey("Board.id", ondelete="CASCADE"))
    requestedByUserId: Mapped[str] = mapped_column(
        "requestedByUserId", String, ForeignKey("User.id", ondelete="CASCADE")
    )
    proposalJson: Mapped[dict] = mapped_column("proposalJson", JSONB, nullable=False)
    expiresAt: Mapped[datetime] = mapped_column("expiresAt", DateTime(timezone=True), nullable=False)
    acceptedAt: Mapped[datetime | None] = mapped_column("acceptedAt", DateTime(timezone=True), nullable=True)
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), default=_utc_now, server_default=func.now()
    )

    board: Mapped["Board"] = relationship(back_populates="generatedProposals")
    requestedBy: Mapped["User"] = relationship(back_populates="generatedProposals")
