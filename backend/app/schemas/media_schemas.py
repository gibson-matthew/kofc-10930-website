from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List


# ============================================================
#  PHOTO RESPONSE
# ============================================================

class PhotoResponse(BaseModel):
    id: int
    album_id: int
    file_path: str
    caption: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
#  ALBUM RESPONSE
# ============================================================

class AlbumResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
#  ALBUM + PHOTOS RESPONSE
# ============================================================

class AlbumWithPhotosResponse(AlbumResponse):
    photos: List[PhotoResponse]
