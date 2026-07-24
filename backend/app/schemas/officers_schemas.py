from pydantic import BaseModel
from app.models.officers import OfficerPosition


class OfficerBase(BaseModel):
    position: OfficerPosition


class OfficerCreate(OfficerBase):
    user_id: int


class OfficerUpdate(OfficerBase):
    pass


class OfficerRead(BaseModel):
    id: int
    position: OfficerPosition
    name: str
    photo: str | None

    class Config:
        orm_mode = True
