from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Text, TIMESTAMP
from app.db.session import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(
        TIMESTAMP, server_default="NOW()"
    )
