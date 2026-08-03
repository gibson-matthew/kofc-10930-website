from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

# Services imported through package __init__.py
from app.services import prayer_service

# Schemas imported through package __init__.py
from app.schemas import prayers_schemas

# Auth dependency for member submissions
from app.auth.dependencies import get_current_user
from app.models import user as user_model


router = APIRouter(prefix="/prayer", tags=["Prayer Requests"])


# ============================================================
#  MEMBER PRAYER REQUEST
# ============================================================

@router.post("/request", response_model=prayers_schemas.PrayerRequestResponse)
async def submit_member_prayer_request(
    payload: prayers_schemas.PrayerRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: user_model.User = Depends(get_current_user),
):
    """
    Authenticated members submit prayer requests.
    """
    prayer = await prayer_service.create(
        db,
        requester_name=f"{current_user.first_name} {current_user.last_name}",
        requester_email=current_user.email,
        is_member=True,
        request_text=payload.request_text,
    )

    if not prayer:
        raise HTTPException(status_code=500, detail="Unable to submit prayer request")

    return prayer


# ============================================================
#  GUEST PRAYER REQUEST
# ============================================================

@router.post("/request/guest", response_model=prayers_schemas.PrayerRequestResponse)
async def submit_guest_prayer_request(
    payload: prayers_schemas.PrayerRequestGuestCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Guests submit prayer requests without authentication.
    """
    prayer = await prayer_service.create(
        db,
        requester_name=payload.requester_name,
        requester_email=payload.requester_email,
        is_member=False,
        request_text=payload.request_text,
    )

    if not prayer:
        raise HTTPException(status_code=500, detail="Unable to submit prayer request")

    return prayer
