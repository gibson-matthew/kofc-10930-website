from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text, TIMESTAMP
from app.db.session import Base


class MediaAlbum(Base):
    __tablename__ = "media_albums"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(
        TIMESTAMP, server_default="NOW()"
    )

    # relationships
    items: Mapped[list["MediaItem"]] = relationship(
        back_populates="album",
        cascade="all, delete-orphan"
    )
