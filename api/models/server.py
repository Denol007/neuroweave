import enum

from sqlalchemy import BigInteger, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class ServerPlan(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Server(Base, TimestampMixin):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    icon_url: Mapped[str | None] = mapped_column(Text)
    member_count: Mapped[int] = mapped_column(BigInteger, default=0)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    plan: Mapped[ServerPlan] = mapped_column(
        Enum(ServerPlan), default=ServerPlan.FREE, nullable=False
    )

    channels = relationship("Channel", back_populates="server", cascade="all, delete-orphan")
