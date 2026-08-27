from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text, TIMESTAMP, ForeignKey
from app.db.session import Base


class MediaItem(Base):
    __tablename__ = "media_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    album_id: Mapped[int] = mapped_column(
        ForeignKey("media_albums.id", ondelete="CASCADE")
    )

    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(
        TIMESTAMP, server_default="NOW()"
    )

    # relationships
    album: Mapped["MediaAlbum"] = relationship(back_populates="items")
