from sqlalchemy import Column, Integer, Text, TIMESTAMP, ForeignKey
from backend.app.db.session import Base

class MediaAlbum(Base):
    __tablename__ = "media_albums"

    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    created_at = Column(TIMESTAMP)

class MediaItem(Base):
    __tablename__ = "media_items"

    id = Column(Integer, primary_key=True)
    album_id = Column(Integer, ForeignKey("media_albums.id"))
    file_path = Column(Text, nullable=False)
    caption = Column(Text)
    created_at = Column(TIMESTAMP)
