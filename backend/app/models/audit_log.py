from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Text, TIMESTAMP, ForeignKey, text
from datetime import datetime
from app.db.session import Base

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    action: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("NOW()"),
        nullable=False
    )
