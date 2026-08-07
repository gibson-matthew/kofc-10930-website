from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Text, TIMESTAMP, ForeignKey, text
from datetime import datetime
from app.db.session import Base

class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)

    uploaded_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("NOW()"),
        nullable=False
    )
