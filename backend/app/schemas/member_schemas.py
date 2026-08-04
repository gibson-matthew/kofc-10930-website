from datetime import datetime
from pydantic import BaseModel
from typing import Optional


# ============================================================
#  MEMBER PROFILE
# ============================================================

class MemberProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    class Config:
        from_attributes = True


class MemberProfileResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    address: Optional[str]
    # city: Optional[str]
    # state: Optional[str]
    # zip_code: Optional[str]

    class Config:
        from_attributes = True


# ============================================================
#  MEMBER DOCUMENTS
# ============================================================

class MemberDocumentResponse(BaseModel):
    id: int
    # member_id: int
    title: str
    file_path: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ============================================================
#  EVENTS
# ============================================================

class EventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    location: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    is_public: bool

    class Config:
        from_attributes = True


class EventVolunteerResponse(BaseModel):
    id: int
    event_id: int
    user_id: int
    hours: Optional[float]
    notes: Optional[str]

    class Config:
        from_attributes = True


class EventHoursResponse(BaseModel):
    hours: float

    class Config:
        from_attributes = True


# ============================================================
#  PROGRAMS & COMMITTEES
# ============================================================

class CommitteeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True


class ProgramResponse(BaseModel):
    id: int
    committee_id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True
