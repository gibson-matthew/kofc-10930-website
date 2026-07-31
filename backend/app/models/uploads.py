from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Text, TIMESTAMP
from app.db.session import Base


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_at: Mapped[str] = mapped_column(
        TIMESTAMP, server_default="NOW()"
    )
