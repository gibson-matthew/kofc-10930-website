from datetime import datetime
from pydantic import BaseModel


class NewsResponse(BaseModel):
    id: int
    title: str
    body: str
    published_at: datetime | None
    author_id: int | None

    class Config:
        orm_mode = True
