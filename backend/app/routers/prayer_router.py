from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import prayer_service
from app.schemas import prayers_schemas
from app.auth.dependencies import get_current_user
from app.models import user as user_model


router = APIRouter(tags=["Prayer Requests"])


# ============================================================
#  MEMBER PRAYER REQUEST
# ============================================================

@router.post(
    "/request",
    response_model=prayers_schemas.PrayerRequestResponse,
)
async def submit_member_prayer_request(
    payload: prayers_schemas.PrayerRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: user_model.User = Depends(get_current_user),
):
    """
    Authenticated members submit prayer requests.
    """

    prayer = await prayer_service.create_member(
        db=db,
        requester_name=f"{current_user.first_name} {current_user.last_name}",
        requester_email=current_user.email,
        request_text=payload.request_text,
    )

    if not prayer:
        raise HTTPException(
            status_code=500,
            detail="Unable to submit prayer request",
        )

    return prayer


# ============================================================
#  GUEST PRAYER REQUEST
# ============================================================

@router.post(
    "/request/guest",
    response_model=prayers_schemas.PrayerRequestResponse,
)
async def submit_guest_prayer_request(
    payload: prayers_schemas.PrayerRequestGuestCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Guests submit prayer requests without authentication.
    """

    prayer = await prayer_service.create_guest(
        db=db,
        payload=payload,
    )

    if not prayer:
        raise HTTPException(
            status_code=500,
            detail="Unable to submit prayer request",
        )

    return prayer


# ============================================================
#  PUBLIC LISTING (optional, matches API spec)
# ============================================================

@router.get(
    "/public",
    response_model=list[prayers_schemas.PrayerRequestResponse],
)
async def list_public_prayer_requests(
    db: AsyncSession = Depends(get_db),
):
    """
    Public listing of all prayer requests.
    """
    return await prayer_service.list_all(db)


# ============================================================
#  PUBLIC DETAIL (optional, matches API spec)
# ============================================================

@router.get(
    "/public/{prayer_id}",
    response_model=prayers_schemas.PrayerRequestResponse,
)
async def get_public_prayer_request(
    prayer_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Public detail view of a single prayer request.
    """
    prayer = await prayer_service.get_by_id(db, prayer_id)

    if not prayer:
        raise HTTPException(
            status_code=404,
            detail="Prayer request not found",
        )

    return prayer
