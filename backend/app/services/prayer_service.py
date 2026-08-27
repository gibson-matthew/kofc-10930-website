from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from typing import List, Optional

from app.models.prayer_requests import PrayerRequest
from app.schemas.prayers_schemas import (
    PrayerRequestCreate,
    PrayerRequestGuestCreate,
    PrayerRequestResponse,
)


class PrayerService:
    """
    Service layer for handling prayer request creation and retrieval.
    This service does NOT inherit from BaseCRUDService because
    prayer requests require custom creation logic for members vs guests.
    """

    # ------------------------------------------------------------
    # CREATE — MEMBER
    # ------------------------------------------------------------
    async def create_member(
        self,
        db: AsyncSession,
        requester_name: str,
        requester_email: str,
        request_text: str,
    ) -> PrayerRequestResponse:

        stmt = (
            insert(PrayerRequest)
            .values(
                requester_name=requester_name,
                requester_email=requester_email,
                is_member=True,
                request_text=request_text,
            )
            .returning(PrayerRequest)
        )

        result = await db.execute(stmt)
        await db.commit()

        prayer = result.scalar_one()
        return PrayerRequestResponse.from_orm(prayer)

    # ------------------------------------------------------------
    # CREATE — GUEST
    # ------------------------------------------------------------
    async def create_guest(
        self,
        db: AsyncSession,
        payload: PrayerRequestGuestCreate,
    ) -> PrayerRequestResponse:

        stmt = (
            insert(PrayerRequest)
            .values(
                requester_name=payload.requester_name,
                requester_email=payload.requester_email,
                is_member=False,
                request_text=payload.request_text,
            )
            .returning(PrayerRequest)
        )

        result = await db.execute(stmt)
        await db.commit()

        prayer = result.scalar_one()
        return PrayerRequestResponse.from_orm(prayer)

    # ------------------------------------------------------------
    # GET ALL (for public listing)
    # ------------------------------------------------------------
    async def list_all(
        self,
        db: AsyncSession,
    ) -> List[PrayerRequestResponse]:

        result = await db.execute(select(PrayerRequest))
        rows = result.scalars().all()

        return [PrayerRequestResponse.from_orm(row) for row in rows]

    # ------------------------------------------------------------
    # GET BY ID
    # ------------------------------------------------------------
    async def get_by_id(
        self,
        db: AsyncSession,
        prayer_id: int,
    ) -> Optional[PrayerRequestResponse]:

        result = await db.execute(
            select(PrayerRequest).where(PrayerRequest.id == prayer_id)
        )
        prayer = result.scalar_one_or_none()

        if prayer:
            return PrayerRequestResponse.from_orm(prayer)

        return None


# Instantiate service
prayer_service = PrayerService()
