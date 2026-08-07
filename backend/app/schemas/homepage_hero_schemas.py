from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class HomepageHeroImageResponse(BaseModel):
    id: int
    url: str
    caption: Optional[str]
    order: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class HomepageHeroImageCreate(BaseModel):
    url: str
    caption: Optional[str] = None
    order: int = 0
    is_active: bool = True


class HomepageHeroImageUpdate(BaseModel):
    url: Optional[str] = None
    caption: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None
