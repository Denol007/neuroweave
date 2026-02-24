import enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class ArticleType(str, enum.Enum):
    TROUBLESHOOTING = "troubleshooting"
    QUESTION_ANSWER = "question_answer"
    GUIDE = "guide"
    DISCUSSION_SUMMARY = "discussion_summary"


class Article(Base, TimestampMixin):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    thread_id: Mapped[int] = mapped_column(
        ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    article_type: Mapped[str] = mapped_column(String(30), default="troubleshooting", nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(20), default="discord", nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(Text)
    symptom: Mapped[str] = mapped_column(Text, nullable=False)
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    solution: Mapped[str] = mapped_column(Text, nullable=False)
    code_snippet: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(50), default="general", nullable=False, index=True)
    framework: Mapped[str | None] = mapped_column(String(100))
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(50)), default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    thread_summary: Mapped[str] = mapped_column(Text, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    embedding = mapped_column(Vector(384))
    is_visible: Mapped[bool] = mapped_column(default=True)

    thread = relationship("Thread", back_populates="article")
