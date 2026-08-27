from datetime import datetime
from typing import Optional
from pydantic import BaseModel


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

    class Config:
        from_attributes = True


# ============================================================
#  MEMBER DOCUMENTS
# ============================================================

class MemberDocumentResponse(BaseModel):
    id: int
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


# ============================================================
#  OFFICERS
# ============================================================

class OfficerResponse(BaseModel):
    id: int
    title: str
    name: str
    email: Optional[str]
    phone: Optional[str]

    class Config:
        from_attributes = True


# ============================================================
#  DIRECTORS
# ============================================================

class DirectorResponse(BaseModel):
    id: int
    name: str
    position: Optional[str]
    email: Optional[str]
    phone: Optional[str]

    class Config:
        from_attributes = True


# ============================================================
#  ASSEMBLIES
# ============================================================

class AssemblyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True


# ============================================================
#  NEWS
# ============================================================

class NewsResponse(BaseModel):
    id: int
    title: str
    body: str
    published_at: Optional[datetime]
    author_id: Optional[int]

    class Config:
        from_attributes = True


# ============================================================
#  VOTING
# ============================================================

class VotingResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    vote_month: Optional[int]
    vote_year: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
