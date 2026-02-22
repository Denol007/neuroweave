import enum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class ThreadStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    RESOLVED = "resolved"
    NOISE = "noise"
    INCOMPLETE = "incomplete"
    FAILED = "failed"


class Thread(Base, TimestampMixin):
    __tablename__ = "threads"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_ids: Mapped[list[str]] = mapped_column(ARRAY(String(32)), default=list)
    status: Mapped[ThreadStatus] = mapped_column(
        Enum(ThreadStatus), default=ThreadStatus.PENDING, nullable=False, index=True
    )
    cluster_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    checkpoint_thread_id: Mapped[str | None] = mapped_column(String(200), unique=True)

    channel = relationship("Channel")
    article = relationship("Article", back_populates="thread", uselist=False)
