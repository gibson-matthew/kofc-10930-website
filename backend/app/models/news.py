from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text, TIMESTAMP, ForeignKey
from app.db.session import Base


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[str] = mapped_column(
        TIMESTAMP, server_default="NOW()"
    )

    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # optional relationship
    author: Mapped["User"] = relationship()
