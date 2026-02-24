import enum

from sqlalchemy import BigInteger, Enum, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class ServerPlan(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SourceType(str, enum.Enum):
    DISCORD = "discord"
    GITHUB = "github"
    DISCOURSE = "discourse"


class Server(Base, TimestampMixin):
    __tablename__ = "servers"
    __table_args__ = (
        UniqueConstraint("source_type", "external_id", name="uq_server_source_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(20), default="discord", nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    discord_id: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    icon_url: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    member_count: Mapped[int] = mapped_column(BigInteger, default=0)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    source_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    plan: Mapped[ServerPlan] = mapped_column(
        Enum(ServerPlan), default=ServerPlan.FREE, nullable=False
    )

    channels = relationship("Channel", back_populates="server", cascade="all, delete-orphan")
