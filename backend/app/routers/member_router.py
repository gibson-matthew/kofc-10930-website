from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert

from app.db.session import get_db
from app.auth.dependencies import get_current_user

from app.models.user import User
from app.models.documents import Document
from app.models.events import Event
from app.models.event_volunteers import EventVolunteer
from app.models.programs import Program
from app.models.committees import Committee

# New models required by API spec
from app.models.officers import Officer
from app.models.directors import Director
from app.models.assemblies import Assembly
from app.models.announcements import Announcement
from app.models.voting import VotingRecord

from app.schemas.member_schemas import (
    MemberProfileUpdate,
    MemberProfileResponse,
    MemberDocumentResponse,
    EventResponse,
    EventVolunteerResponse,
    EventHoursResponse,
    ProgramResponse,
    CommitteeResponse,
    OfficerResponse,
    DirectorResponse,
    AssemblyResponse,
    AnnouncementResponse,
    VotingResponse,
)


router = APIRouter(prefix="/member", tags=["Member"])


# ============================================================
#  MEMBER STATUS CHECK
# ============================================================

@router.get("/status")
async def public_status():
    return {"status": "ok", "message": "Member API is running"}


# ============================================================
#  MEMBER PROFILE
# ============================================================

@router.get("/profile", response_model=MemberProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    return MemberProfileResponse.from_orm(current_user)


@router.put("/profile", response_model=MemberProfileResponse)
async def update_profile(
    payload: MemberProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)
    return MemberProfileResponse.from_orm(current_user)


# ============================================================
#  MEMBER DOCUMENTS
# ============================================================

@router.get("/documents", response_model=list[MemberDocumentResponse])
async def get_member_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Document))
    docs = result.scalars().all()
    return [MemberDocumentResponse.from_orm(d) for d in docs]


# ============================================================
#  MEMBER ANNOUNCEMENTS
# ============================================================

@router.get("/announcements", response_model=list[AnnouncementResponse])
async def get_member_announcements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Announcement))
    rows = result.scalars().all()
    return [AnnouncementResponse.from_orm(a) for a in rows]


# ============================================================
#  MEMBER CALENDAR (placeholder)
# ============================================================

@router.get("/calendar")
async def get_member_calendar(current_user: User = Depends(get_current_user)):
    return {"message": "Calendar endpoint not yet implemented"}


# ============================================================
#  MEMBER EVENTS
# ============================================================

@router.get("/events", response_model=list[EventResponse])
async def list_member_events(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Event))
    events = result.scalars().all()
    return [EventResponse.from_orm(e) for e in events]


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_member_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return EventResponse.from_orm(event)


@router.post("/events/{event_id}/volunteer", response_model=EventVolunteerResponse)
async def volunteer_for_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        insert(EventVolunteer)
        .values(event_id=event_id, user_id=current_user.id, hours=0, notes=None)
        .returning(EventVolunteer)
    )
    result = await db.execute(stmt)
    await db.commit()
    volunteer = result.scalar_one()
    return EventVolunteerResponse.from_orm(volunteer)


@router.post("/events/{event_id}/hours", response_model=EventHoursResponse)
async def submit_event_hours(
    event_id: int,
    payload: EventHoursResponse,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        insert(EventVolunteer)
        .values(event_id=event_id, user_id=current_user.id, hours=payload.hours)
        .returning(EventVolunteer)
    )
    result = await db.execute(stmt)
    await db.commit()
    hours = result.scalar_one()
    return EventHoursResponse.from_orm(hours)


# ============================================================
#  MEMBER PROGRAMS
# ============================================================

@router.get("/programs", response_model=list[CommitteeResponse])
async def list_committees(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Committee))
    committees = result.scalars().all()
    return [CommitteeResponse.from_orm(c) for c in committees]


@router.get("/programs/{committee_id}", response_model=list[ProgramResponse])
async def list_programs_by_committee(
    committee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Program).where(Program.committee_id == committee_id))
    programs = result.scalars().all()
    return [ProgramResponse.from_orm(p) for p in programs]


@router.get("/programs/{committee_id}/{program_id}", response_model=ProgramResponse)
async def get_program_detail(
    committee_id: int,
    program_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Program).where(
            Program.committee_id == committee_id,
            Program.id == program_id,
        )
    )
    program = result.scalar_one_or_none()

    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    return ProgramResponse.from_orm(program)


# ============================================================
#  MEMBER OFFICERS
# ============================================================

@router.get("/officers", response_model=list[OfficerResponse])
async def get_member_officers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Officer))
    officers = result.scalars().all()
    return [OfficerResponse.from_orm(o) for o in officers]


# ============================================================
#  MEMBER DIRECTORS
# ============================================================

@router.get("/directors", response_model=list[DirectorResponse])
async def get_member_directors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Director))
    directors = result.scalars().all()
    return [DirectorResponse.from_orm(d) for d in directors]


# ============================================================
#  MEMBER ASSEMBLIES
# ============================================================

@router.get("/assemblies", response_model=list[AssemblyResponse])
async def get_member_assemblies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Assembly))
    assemblies = result.scalars().all()
    return [AssemblyResponse.from_orm(a) for a in assemblies]


# ============================================================
#  MEMBER VOTING
# ============================================================

@router.get("/voting", response_model=list[VotingResponse])
async def get_member_voting(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(VotingRecord))
    votes = result.scalars().all()
    return [VotingResponse.from_orm(v) for v in votes]


@router.get("/voting/{year}/{month}", response_model=list[VotingResponse])
async def get_member_voting_by_month(
    year: int,
    month: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(VotingRecord).where(
            VotingRecord.year == year,
            VotingRecord.month == month,
        )
    )
    votes = result.scalars().all()
    return [VotingResponse.from_orm(v) for v in votes]
