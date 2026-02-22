from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base, TimestampMixin


class DatasetExport(Base, TimestampMixin):
    __tablename__ = "dataset_exports"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    format: Mapped[str] = mapped_column(String(20), default="jsonl", nullable=False)
    record_count: Mapped[int] = mapped_column(BigInteger, default=0)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    c2pa_manifest_hash: Mapped[str | None] = mapped_column(String(128))

    # PII audit
    pii_audit_hash: Mapped[str | None] = mapped_column(String(128))
    consent_verified: Mapped[bool] = mapped_column(default=False)
